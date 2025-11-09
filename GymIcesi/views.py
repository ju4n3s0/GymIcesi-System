# GymIcesi/views.py

from django.utils import timezone
from django.utils.text import slugify
from bson import ObjectId
from django.contrib.auth.decorators import login_required,user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages

from django.contrib.auth import authenticate, login
from .forms import ExerciseForm, RoutineForm, TrainerAssignForm, AssignRoutineForm
from .models import User, Employee
from . import mongo_utils
from .forms import ProgressLogForm
import datetime as dt


def staff_required(u):
    return u.is_authenticated and (u.is_staff or u.is_superuser)



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
@user_passes_test(is_trainer_or_admin)  
def routine_assign(request):
    """
    Permite a un trainer asignar una rutina (Mongo) a cualquier usuario (SQL).
    GUIADA por el patrón de routine_create:
      - Lee las rutinas desde Mongo (colección 'routines').
      - Inserta una asignación en Mongo (colección 'user_routines').
    """
    db = mongo_utils.get_db()
    routines_coll = db.routines
    assignments_coll = db.user_routines  # NUEVA colección

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

            # 3) Regla anti-duplicado por día (opcional, igual que unique_together)
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
                return redirect("assignment_list")

            # 4) Construir documento (siguiendo tu estilo camelCase y createdAt)
            doc = {
                "routineId": routine_oid,
                "routineName": routine_doc.get("name"),
                "targetUserId": target_user.id,
                "targetUsername": target_user.username,
                # quién asigna:
                "assignedByUserId": getattr(request.user, "id", None),
                "assignedByUsername": getattr(request.user, "username", None),
                "assignedByEmployeeId": getattr(request.user, "employee_id", None),
                # datos de negocio:
                "startDate": start_date.isoformat(),
                "notes": data.get("notes", ""),
                "isActive": True,
                # auditoría:
                "createdAt": timezone.now(),
            }

            assignments_coll.insert_one(doc)
            messages.success(request, "Rutina asignada correctamente.")
            return redirect("assignment_list")
    else:
        form = AssignRoutineForm()

    return render(request, "workouts/routine_assign.html", {"form": form})

@login_required
@user_passes_test(is_trainer_or_admin)
def assignment_list(request):
    db = mongo_utils.get_db()
    assignments = list(db.user_routines.find().sort("createdAt", -1))
    return render(request, "admin/assignment_list.html", {"assignments": assignments})

# ---------- REGISTRAR PROGRESO DEL USUARIO ----------

@login_required
def progress_list(request):
    user_id = request.user.username  # en tu esquema relacional
    logs = mongo_utils.list_progress_logs(user_id)

    # Resolver nombres de ejercicios
    db = mongo_utils.get_db()
    exercises = {str(e["_id"]): e["name"] for e in db.exercises.find({}, {"_id": 1, "name": 1})}

    for log in logs:
        log["exercise_name"] = exercises.get(str(log["exerciseId"]), "Desconocido")

    context = {"records": logs}
    return render(request, "progres/progress_list.html", context)


@login_required
def progress_create(request):
    if request.method == "POST":
        form = ProgressLogForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            mongo_utils.insert_progress_log(
                user_id=request.user.username,
                exercise_id=cd["exercise"],
                date=cd["date"],
                repetitions=cd.get("repetitions"),
                duration=cd.get("duration"),
                effort=cd.get("effort"),
                notes=cd.get("notes"),
            )
            messages.success(request, "Progreso registrado correctamente ✅")
            return redirect("progress_list")
    else:
        form = ProgressLogForm()

    return render(request, "progress/progress_form.html", {"form": form})

