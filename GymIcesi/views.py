# GymIcesi/views.py

from django.utils import timezone
from django.utils.text import slugify
from bson import ObjectId
from django.contrib.auth.decorators import login_required,user_passes_test
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages

from django.contrib.auth import authenticate, login
from .forms import ExerciseForm, RoutineForm, TrainerAssignForm, AssignRoutineForm
from .models import User, Employee
from GymIcesi.models import Student, Employee
from .models import User as UniUser 
from . import mongo_utils
from django.core.paginator import Paginator
from django.db.models import Q
    

def assignment_show(request):
    students = (UniUser.objects
                .filter(role="STUDENT", is_active=True)
                .select_related("student")
                .order_by("username"))
    
    trainers = (UniUser.objects
                .filter(role="EMPLOYEE", is_active=True, employee__isnull=False)
                .select_related("employee")
                .order_by("employee__last_name", "employee__first_name"))

    active_map = mongo_utils.get_active_map([u.username for u in students])

    trainer_ids = {
        str(d.get("trainerId", "")).strip()
        for d in active_map.values() if d.get("trainerId")
    }
    emp_map = {str(e.id).strip(): e for e in Employee.objects.filter(id__in=trainer_ids)}

    # Enriquecer cada estudiante con atributos SIN "_"
    for s in students:
        a = active_map.get(s.username)  # dict o None
        s.active_assignment = a
        key = str(a.get("trainerId", "")).strip() if a else ""
        s.assigned_trainer = emp_map.get(key)

    return render(request, "admin/assignment_list.html", {
        "students": students,
        "trainers": trainers,
    })



# ---------- CATÁLOGO DE EJERCICIOS ----------

@login_required
def exercise_list(request):
    """
    Vista para:
    - Ver el catálogo de ejercicios (predefinidos + personalizados).
    - Crear nuevos ejercicios con los campos del enunciado.

    Usa la colección 'exercises' en MongoDB.
    La colección tiene un jsonSchema que exige:
    slug, name, muscleGroup, equipment, createdAt
    por eso los incluimos siempre.
    """
    db = mongo_utils.get_db()
    collection = db.exercises

    if request.method == "POST":
        form = ExerciseForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            doc = {
                # Campos requeridos por el validador en Atlas
                "slug": slugify(data["name"]),        # p.ej. "Press banca" -> "press-banca"
                "name": data["name"],
                "muscleGroup": "General",             # valor por defecto (puedes cambiarlo luego)
                "equipment": "Sin equipo",            # valor por defecto
                "createdAt": timezone.now(),          # ojo: camelCase, no created_at

                # Campos del enunciado
                "type": data["type"],                 # cardio | fuerza | movilidad
                "description": data["description"],
                "duration": data["duration"],         # minutos
                "difficulty": data["difficulty"],     # baja | media | alta
                "video_url": data["video_url"],

                # Metadatos
                "created_by": request.user.username,
                "is_public": True,
            }

            collection.insert_one(doc)
            messages.success(request, "Ejercicio creado correctamente.")
            return redirect("exercise_list")
    else:
        form = ExerciseForm()

    # Listar ejercicios ordenados por nombre
    exercises = list(collection.find().sort("name", 1))

    context = {
        "form": form,
        "exercises": exercises,
    }
    return render(request, "workouts/exercise_list.html", context)


# ---------- LISTA DE RUTINAS DEL USUARIO ----------

@login_required
def routine_list(request):
    """
    Lista las rutinas de ejercicio del usuario autenticado.
    Lee desde la colección 'routines' en MongoDB.
    """
    db = mongo_utils.get_db()
    routines = db.routines.find(
        {"userId": request.user.username}
    ).sort("createdAt", -1)

    context = {
        "routines": routines,
    }
    return render(request, "workouts/routine_list.html", context)


# ---------- CREACIÓN DE RUTINAS ----------

@login_required
def routine_create(request):
    """
    Permite al usuario registrar una rutina de ejercicio:
    - Elige ejercicios predefinidos del catálogo (colección 'exercises').
    - Si necesita un ejercicio personalizado, primero lo crea en exercise_list.
    """
    db = mongo_utils.get_db()
    exercises_coll = db.exercises
    routines_coll = db.routines

    if request.method == "POST":
        form = RoutineForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # La rutina viene con una lista de IDs de ejercicios (strings) desde el form
            exercise_ids = [ObjectId(eid) for eid in data["exercises"]]

            exercise_docs = list(
                exercises_coll.find({"_id": {"$in": exercise_ids}})
            )

            items = []
            for ex in exercise_docs:
                items.append(
                    {
                        "exerciseId": ex["_id"],
                        "exerciseName": ex["name"],
                        "type": ex.get("type"),
                        "duration": ex.get("duration"),
                        "difficulty": ex.get("difficulty"),
                        "video_url": ex.get("video_url"),
                    }
                )

            routines_coll.insert_one(
                {
                    "userId": request.user.username,
                    "name": data["name"],
                    "description": data["description"],
                    "items": items,
                    "createdAt": timezone.now(),
                    "active": True,
                }
            )

            messages.success(request, "Rutina creada correctamente.")
            return redirect("routine_list")
    else:
        form = RoutineForm()

    context = {
        "form": form,
    }
    return render(request, "workouts/routine_create.html", context)


def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')  
        password = request.POST.get('password')
        print("DEBUG: Intentando autenticar al usuario:", username)
        user = authenticate(request, username=username, password=password)

        if user is not None:
            user.refresh_from_db()

            if user.is_superuser:
                print("DEBUG: El usuario es superusuario.")
                messages.error(request, "El superusuario solo puede acceder al admin.")
                return redirect('login')

            print("DEBUG: Login exitoso.")
            login(request, user)
            return redirect('carreerFilter')

        else:
            print("DEBUG: Falló la autenticación para el usuario:", username)
            messages.error(request, "La contraseña o el usuario son incorrectos.")
    
    return render(request, 'registration/login.html')


def is_trainer(user):
    """
    Un usuario es 'trainer' si está autenticado, tiene vínculo a Employee
    y su Employee es de tipo 'Instructor'.
    """
    if not user.is_authenticated:
        return False
    # Si tu User tiene FK 'employee' (managed=False) podemos resolverla:
    try:
        if user.employee_id is None:
            return False
        return Employee.objects.filter(
            id=user.employee_id,
            employee_type__name="Instructor"
        ).exists()
    except Exception:
        return False
    
ALLOWED_EMPLOYEE_TYPES = {"Instructor", "Administrador", "Admin"}
ALLOWED_ROLES = {"trainer", "admin"}

def is_trainer_or_admin(user):
    """
    Devuelve True si el usuario:
      1) Tiene role en {'trainer','admin'}, o
      2) Es superuser/staff de Django, o
      3) Su Employee tiene tipo en {'Instructor','Administrador','Admin'}.
    """
    if not user.is_authenticated:
        return False

    # (1) Vía rápida por campo role, si existe
    role = getattr(user, "role", None)
    if role in ALLOWED_ROLES:
        return True

    # (2) Flags estándar de Django
    if user.is_superuser or user.is_staff:
        return True

    # (3) Revisión por Employee (clave foránea en el user)
    emp_id = getattr(user, "employee_id", None)
    if not emp_id:
        return False

    return Employee.objects.filter(
        id=emp_id,
        employee_type__name__in=ALLOWED_EMPLOYEE_TYPES
    ).exists()

@login_required
#@user_passes_test(is_trainer_or_admin)
def routine_assign(request):
    """
    Permite a un trainer/admin asignar una rutina (Mongo) a cualquier usuario (SQL),
    siguiendo el patrón de routine_create.
    """
    db = mongo_utils.get_db()
    routines_coll = db.routines
    assignments_coll = db.user_routines  # colección nueva

    if request.method == "POST":
        form = AssignRoutineForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data

            # 1) Validar rutina Mongo
            try:
                routine_oid = ObjectId(data["routine"])
            except Exception:
                messages.error(request, "Rutina inválida.")
                return render(request, "workouts/routine_assign.html", {"form": form})

            routine_doc = routines_coll.find_one({"_id": routine_oid})
            if not routine_doc:
                messages.error(request, "No se encontró la rutina seleccionada.")
                return render(request, "workouts/routine_assign.html", {"form": form})

            # 2) Usuario objetivo (SQL)
            target_user = data["user"]

            # 3) Antiduplicado por día
            start_date = data["start_date"]
            existing = assignments_coll.find_one({
                "routineId": routine_oid,
                "targetUserId": target_user.id,
                "startDate": start_date.isoformat(),
            })
            if existing:
                messages.warning(
                    request,
                    "Ya existe una asignación de esta rutina para ese usuario en la misma fecha."
                )
                return redirect("user_routine_history", user_id=target_user.id)

            # 4) Documento a insertar
            doc = {
                "routineId": routine_oid,
                "routineName": routine_doc.get("name"),
                "targetUserId": target_user.id,
                "targetUsername": target_user.username,
                "assignedByUserId": getattr(request.user, "id", None),
                "assignedByUsername": getattr(request.user, "username", None),
                "assignedByEmployeeId": getattr(request.user, "employee_id", None),
                "startDate": start_date.isoformat(),
                "notes": data.get("notes", ""),
                "isActive": True,
                "createdAt": timezone.now(),
            }

            assignments_coll.insert_one(doc)
            messages.success(request, "Rutina asignada correctamente.")
            return redirect("user_routine_history", user_id=target_user.id)
        # Si el form no es válido, se cae al render de abajo con errores
    # GET (prefill)
    else:
        initial = {}
        user_pk = request.GET.get("user")
        if user_pk:                          
            initial["user"] = user_pk
        form = AssignRoutineForm(initial=initial)

    # Al construir el documento:
    doc = {
        "routineId": routine_oid,
        "routineName": routine_doc.get("name"),
        "targetUserId": target_user.pk,               
        "targetUsername": target_user.username,
        "assignedByUserId": request.user.pk,        
        "assignedByUsername": request.user.username,
        "assignedByEmployeeId": getattr(request.user, "employee_id", None),
        "startDate": start_date.isoformat(),
        "notes": data.get("notes", ""),
        "isActive": True,
        "createdAt": timezone.now(),
    }


    return redirect("user_routine_history", user_pk=target_user.pk) 


@login_required
#@user_passes_test(is_trainer_or_admin)
def routine_users(request):
    """
    Lista de usuarios visibles para trainer/admin.
    Usa pk (no 'id') y busca por username/role (campos existentes).
    """
    q = (request.GET.get("q") or "").strip()

    users_qs = (
        User.objects
        .filter(is_active=True)
        .exclude(pk=request.user.pk)                  # ⬅️ reemplaza id por pk
    )

    if q:
        users_qs = users_qs.filter(
            Q(username__icontains=q) | Q(role__icontains=q)  # ⬅️ busca en campos reales
        )

    users_qs = users_qs.order_by("username")          # ⬅️ ordena por campo real

    paginator = Paginator(users_qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "workouts/routine_users.html", {
        "page_obj": page_obj,
        "query": q,
    })


@login_required
#@user_passes_test(is_trainer_or_admin)
def user_routine_history(request, user_pk: str):
    target_user = get_object_or_404(User, pk=user_pk, is_active=True)  # ⬅️ pk, no id

    db = mongo_utils.get_db()
    assignments = list(
        db.user_routines.find({"targetUserId": target_user.pk}).sort("createdAt", -1)
    )

    state = (request.GET.get("state") or "").lower()
    if state == "active":
        assignments = [a for a in assignments if a.get("isActive", True)]
    elif state == "inactive":
        assignments = [a for a in assignments if not a.get("isActive", True)]

    return render(request, "workouts/user_routine_history.html", {
        "target_user": target_user,
        "assignments": assignments,
        "state": state,
    })




def assignment_quick(request):
        student_username = (request.POST.get("student_username") or "").strip()
        trainer_username  = (request.POST.get("trainer_username") or "").strip()
        try:
            suser = UniUser.objects.get(username=student_username, role="STUDENT")
        except UniUser.DoesNotExist:
            messages.error(request, "Estudiante inválido.")
            return redirect("assignment_show")

        try:
            tuser = UniUser.objects.get(username=trainer_username, role="EMPLOYEE")
        except UniUser.DoesNotExist:
            messages.error(request, "Entrenador inválido.")
            return redirect("assignment_show")

        if not tuser.employee_id:
            messages.error(request, "El entrenador seleccionado no tiene Employee asociado.")
            return redirect("assignment_show")
        
        mongo_utils.upsert_active_assignment(
            user_id=suser.username,
            trainer_id=tuser.employee_id,
        )

        emp = tuser.employee  # objeto Employee
        emp_name = f"{emp.first_name} {emp.last_name}" if emp else f"@{tuser.username}"
        messages.success(request, f"@{suser.username} asignado a {emp_name}.")
        return redirect("assignment_show")
