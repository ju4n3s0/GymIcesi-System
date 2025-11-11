# GymIcesi/views.py

import csv
from django.http import HttpResponse
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
from .forms import ProgressLogForm
import datetime as dt

from django.core.paginator import Paginator
from django.db.models import Q

def admin_role(user):
    if not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False):
        return True
    emp_id = getattr(user, "employee_id", None)
    if not emp_id:
        return False
    return Employee.objects.filter(
        id = emp_id,
        employee_type = "Administrativo"
    ).exists()

@login_required
@user_passes_test(admin_role)
def assignment_show(request):
    students = (UniUser.objects
                .filter(role="STUDENT", is_active=True)
                .select_related("student")
                .order_by("username"))
    
    trainers = (UniUser.objects
                .filter(role="EMPLOYEE", is_active=True, employee__isnull=False,employee__employee_type="Instructor")
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

@login_required
@user_passes_test(admin_role)
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

def _resolve_user_from_param(param: str):
    """
    Devuelve un User por pk (numérico) o por username (string).
    """
    if not param:
        return None
    if param.isdigit():
        return User.objects.filter(pk=int(param), is_active=True).first()
    return User.objects.filter(username=param, is_active=True).first()


@login_required
#@user_passes_test(is_trainer_or_admin)
def routine_assign(request):
    """
    Permite a un trainer asignar una rutina (Mongo) a cualquier usuario (SQL).
    GUIADA por el patrón de routine_create:
      - Lee las rutinas desde Mongo (colección 'routines').
      - Inserta una asignación en Mongo (colección 'user_routines').
    """
    db = mongo_utils.get_db()
    routines_coll = db.routines
    assignments_coll = db.user_routines  # colección de asignaciones

    if request.method == "POST":
        form = AssignRoutineForm(request.POST)
        if not form.is_valid():
            return render(request, "workouts/routine_assign.html", {"form": form})

        data = form.cleaned_data

        # 1) Validar rutina Mongo (solo en POST)
        routine_id_str = data["routine"]
        try:
            routine_oid = ObjectId(routine_id_str)
        except Exception:
            messages.error(request, "Rutina inválida.")
            return render(request, "workouts/routine_assign.html", {"form": form})

        routine_doc = routines_coll.find_one({"_id": routine_oid})
        if not routine_doc:
            messages.error(request, "No se encontró la rutina seleccionada.")
            return render(request, "workouts/routine_assign.html", {"form": form})

        # 2) Usuario objetivo (SQL) viene del form (ModelChoiceField)
        target_user = data["user"]

        # 3) Regla anti-duplicado por fecha (si tienes índice único, esto es preventivo)
        start_date = data["start_date"]
        start_iso = start_date.isoformat()

        doc = {
            "routineId": routine_oid,
            "routineName": routine_doc.get("name"),
            "targetUserId": target_user.pk,                  # usa pk, no "id"
            "targetUsername": target_user.username,
            "assignedByUserId": getattr(request.user, "pk", None),
            "assignedByUsername": getattr(request.user, "username", None),
            "assignedByEmployeeId": getattr(request.user, "employee_id", None),
            "startDate": start_iso,
            "notes": data.get("notes", ""),
            "isActive": True,
            "createdAt": timezone.now(),
        }

        try:
            assignments_coll.insert_one(doc)
        except DuplicateKeyError:
            messages.warning(
                request,
                "Ya existe una asignación de esta rutina para ese usuario en la misma fecha."
            )
            return redirect("user_routine_history", user_id=target_user.pk)

        messages.success(request, "Rutina asignada correctamente.")
        return redirect("user_routine_history", user_id=target_user.pk)

    # GET — preparar formulario con 'user' precargado (pk o username)
    initial = {}
    user_param = request.GET.get("user")
    if user_param:
        u = _resolve_user_from_param(user_param)
        if u:
            initial["user"] = u.pk  # precarga el ModelChoiceField

    form = AssignRoutineForm(initial=initial)
    return render(request, "workouts/routine_assign.html", {"form": form})


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

# ---------- REGISTRAR PROGRESO DEL USUARIO ----------



@login_required
def progress_list(request):
    logs = mongo_utils.get_progress_logs_by_user(request.user.username)
    records = []

    for log in logs:
        date = log.get("date")

        for entry in log.get("entries", []):
            exercise_name = entry.get("exerciseName", "Desconocido")

            for set_data in entry.get("sets", []):
                records.append({
                    "date": date,
                    "exercise_name": exercise_name,
                    "reps": set_data.get("reps", "-"),
                    "weight": set_data.get("weight", "-"),
                })

    return render(request, "progress/progress_list.html", {"records": records})



@login_required
def progress_create(request):
    if request.method == "POST":
        form = ProgressLogForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            date = cd["date"]
            if hasattr(date, "year") and not hasattr(date, "hour"):
                import datetime
                date = datetime.datetime.combine(date, datetime.datetime.min.time())

            mongo_utils.insert_progress_log(
                user_id=request.user.username,
                exercise_id=cd["exercise"],  # ✅ pasamos el ObjectId como string
                date=date,
                reps=cd.get("reps"),
                weight=cd.get("weight"),
            )

            messages.success(request, "Progreso registrado correctamente ✅")
            return redirect("progress_list")

        messages.error(request, "Por favor completa correctamente todos los campos ❌")

    else:
        form = ProgressLogForm()

    return render(request, "progress/progress_form.html", {"form": form})
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

    
@login_required
def report_user_assignments(request):
    """
    Informe por usuario: total, activas, inactivas, primera/última fecha, rutinas únicas.
    Soporta ?q=<texto> para filtrar por username/rol y ?format=csv para exportar.
    """
    db = mongo_utils.get_db()
    coll = db.user_routines

    # Agregación en Mongo
    pipeline = [
        {
            "$group": {
                "_id": "$targetUserId",
                "total": {"$sum": 1},
                "activas": {"$sum": {"$cond": ["$isActive", 1, 0]}},
                "inactivas": {"$sum": {"$cond": ["$isActive", 0, 1]}},
                "primeraFecha": {"$min": "$startDate"},
                "ultimaFecha": {"$max": "$startDate"},
                "rutinasUnicas": {"$addToSet": "$routineId"},
            }
        },
        {"$sort": {"total": -1}},
    ]
    agg = list(coll.aggregate(pipeline))

    # Mapeo de usuarios SQL: usamos pk, no "id"
    user_pks = [a["_id"] for a in agg if a.get("_id") is not None]
    # soporta PK string o numérico
    users_qs = User.objects.filter(pk__in=user_pks, is_active=True)

    # Filtro de búsqueda por ?q
    q = (request.GET.get("q") or "").strip()
    if q:
        users_qs = users_qs.filter(Q(username__icontains=q) | Q(role__icontains=q))

    user_map = {str(u.pk): u for u in users_qs}

    # Unimos resultados de Mongo con usuarios SQL
    rows = []
    for a in agg:
        pk = str(a["_id"])
        u = user_map.get(pk)
        if not u:
            continue
        rows.append({
            "user_pk": u.pk,
            "username": u.username,
            "role": getattr(u, "role", ""),
            "total": a.get("total", 0),
            "activas": a.get("activas", 0),
            "inactivas": a.get("inactivas", 0),
            "primeraFecha": a.get("primeraFecha"),
            "ultimaFecha": a.get("ultimaFecha"),
            "rutinasUnicas": len(a.get("rutinasUnicas", [])),
        })

    # Exportación CSV si ?format=csv
    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="reporte_usuarios.csv"'
        writer = csv.writer(resp)
        writer.writerow([
            "username", "role", "total", "activas", "inactivas",
            "rutinas_unicas", "primera_fecha", "ultima_fecha"
        ])
        for r in rows:
            writer.writerow([
                r["username"], r["role"], r["total"], r["activas"], r["inactivas"],
                r["rutinasUnicas"], r["primeraFecha"], r["ultimaFecha"]
            ])
        return resp

    return render(request, "reports/report_user_assignments.html", {
        "rows": rows,
        "query": q,
    })
    
    
@login_required
def report_users_without_routines(request):
    """
    Usuarios activos sin ninguna asignación en Mongo (user_routines).
    Soporta ?q= para filtrar (username/rol) y ?format=csv para exportar.
    """
    db = mongo_utils.get_db()
    coll = db.user_routines

    # Todos los targetUserId con alguna asignación
    assigned_ids = set()
    for doc in coll.aggregate([
        {"$group": {"_id": "$targetUserId"}},
    ]):
        if doc["_id"] is not None:
            assigned_ids.add(str(doc["_id"]))

    qs = User.objects.filter(is_active=True).exclude(pk__in=assigned_ids)

    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(Q(username__icontains=q) | Q(role__icontains=q))

    rows = [
        {"user_pk": u.pk, "username": u.username, "role": getattr(u, "role", "")}
        for u in qs
    ]

    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="usuarios_sin_rutinas.csv"'
        w = csv.writer(resp)
        w.writerow(["username", "role"])
        for r in rows:
            w.writerow([r["username"], r["role"]])
        return resp

    return render(request, "reports/report_users_without_routines.html", {
        "rows": rows,
        "query": q,
    })
    
@login_required
def report_top_exercises(request):
    """
    Top ejercicios más asignados (conteo de items usados en rutinas asignadas).
    Opcional: ?type=cardio|fuerza|movilidad (filtro) y ?limit=20 (top N).
    ?format=csv para exportar.
    """
    db = mongo_utils.get_db()
    ur = db.user_routines
    routines = db.routines

    ex_type = (request.GET.get("type") or "").strip().lower()
    try:
        limit = max(1, int(request.GET.get("limit", "20")))
    except ValueError:
        limit = 20

    # Pipeline: user_routines -> lookup routines -> unwind items -> (filtro por tipo) -> group
    pipeline = [
        {"$lookup": {
            "from": routines.name,
            "localField": "routineId",
            "foreignField": "_id",
            "as": "routine"
        }},
        {"$unwind": "$routine"},
        {"$unwind": "$routine.items"},
    ]
    if ex_type:
        pipeline.append({"$match": {"routine.items.type": {"$regex": f"^{ex_type}$", "$options": "i"}}})
    pipeline += [
        {"$group": {
            "_id": {"name": "$routine.items.exerciseName", "type": "$routine.items.type"},
            "vecesAsignado": {"$sum": 1}
        }},
        {"$sort": {"vecesAsignado": -1, "_id.name": 1}},
        {"$limit": limit},
    ]

    rows = []
    for d in ur.aggregate(pipeline):
        _id = d["_id"] or {}
        rows.append({
            "exerciseName": _id.get("name") or "(sin nombre)",
            "type": _id.get("type") or "",
            "count": d.get("vecesAsignado", 0),
        })

    if request.GET.get("format") == "csv":
        resp = HttpResponse(content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = 'attachment; filename="top_ejercicios.csv"'
        w = csv.writer(resp)
        w.writerow(["exercise_name", "type", "veces_asignado"])
        for r in rows:
            w.writerow([r["exerciseName"], r["type"], r["count"]])
        return resp

    return render(request, "reports/report_top_exercises.html", {
        "rows": rows,
        "filter_type": ex_type,
        "limit": limit,
    })
    
@login_required
#@user_passes_test(is_trainer_or_admin)
def reports_home(request):
    return render(request, "reports/reports_home.html")
