# GymIcesi/views.py

from datetime import datetime
from django.utils import timezone
from django.utils.text import slugify
from bson import ObjectId
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from pymongo import MongoClient

from GymIcesi import settings


from .forms import ExerciseForm, RoutineForm, TrainerAssignForm
from .models import  User, Employee
from . import mongo_utils


def staff_required(u):
    return u.is_authenticated and (u.is_staff or u.is_superuser)

client = MongoClient(
    settings.MONGO_URI,
    serverSelectionTimeoutMS=getattr(settings, "MONGO_TIMEOUT_MS", 1200),
)

# AQUÍ está el cambio importante:
db = client[settings.MONGO_DBNAME]


@login_required
def assaigment_list(request):
    # De momento solo renderiza el template de asignaciones
    return render(request, "admin/assignment_list.html")


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

# ---------------------------------------------------------
# ESTADÍSTICAS MENSUALES (BD RELACIONAL)
# ---------------------------------------------------------

def _get_current_year_month():
    """Devuelve (year, month) del momento actual en UTC."""
    now = datetime.utcnow()
    return now.year, now.month


def registrar_rutina_iniciada(user: User):
    """
    Lógica para actualizar la tabla de estadísticas de USUARIOS
    cada vez que el usuario inicia una rutina.
    Llamamos esta función desde routine_create.
    """
    year, month = _get_current_year_month()

    stats, created = UserMonthlyStats.objects.get_or_create(
        user=user,
        year=year,
        month=month,
        defaults={
            "routines_started": 0,
            "followups_count": 0,
        },
    )
    stats.routines_started += 1
    stats.save()


def registrar_seguimiento_usuario(user: User):
    """
    Si en algún momento implementas 'seguimientos' de rutinas,
    puedes llamar a esta función para sumar el seguimiento
    del usuario en el mes actual.
    """
    year, month = _get_current_year_month()

    stats, created = UserMonthlyStats.objects.get_or_create(
        user=user,
        year=year,
        month=month,
        defaults={
            "routines_started": 0,
            "followups_count": 0,
        },
    )
    stats.followups_count += 1
    stats.save()


def registrar_asignacion_nueva(trainer: Employee):
    """
    Cuando asignes un nuevo usuario a un instructor,
    llama a esta función para reflejarlo en las estadísticas
    de INSTRUCTORES (asignaciones nuevas).
    """
    year, month = _get_current_year_month()

    stats, created = TrainerMonthlyStats.objects.get_or_create(
        trainer=trainer,
        year=year,
        month=month,
        defaults={
            "new_users_assigned": 0,
            "followups_count": 0,
        },
    )
    stats.new_users_assigned += 1
    stats.save()


def registrar_seguimiento_trainer(trainer: Employee):
    """
    Igualmente, cuando un instructor haga un seguimiento,
    llama a esta función para sumarlo.
    """
    year, month = _get_current_year_month()

    stats, created = TrainerMonthlyStats.objects.get_or_create(
        trainer=trainer,
        year=year,
        month=month,
        defaults={
            "new_users_assigned": 0,
            "followups_count": 0,
        },
    )
    stats.followups_count += 1
    stats.save()


def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser


@login_required
@user_passes_test(is_staff_or_superuser)
def stats_dashboard(request):
    """
    Lee las estadísticas mensuales desde la colección de MongoDB `stats_monthly`
    y las muestra en una tabla sencilla.
    """
    stats_collection = db["stats_monthly"]

    # Traer todos los documentos ordenados por año y mes (descendente)
    docs = list(
        stats_collection.find().sort(
            [("year", -1), ("month", -1)]
        )
    )

    # Normalizar los datos a un formato amigable para la plantilla
    user_stats = []
    for d in docs:
        user_stats.append(
            {
                "user_id": d.get("userId", ""),
                "year": d.get("year", ""),
                "month": d.get("month", ""),
                # asumimos que `workouts` es el número de rutinas iniciadas
                "routines_started": d.get("workouts", 0),
                # si tienes un campo de seguimientos, cámbialo aquí
                "followups_count": d.get("followups", 0),
            }
        )

    # Por ahora dejamos los stats de instructores vacíos; la tabla mostrará "No hay datos aún."
    trainer_stats = []

    context = {
        "user_stats": user_stats,
        "trainer_stats": trainer_stats,
    }
    return render(request, "stats_dashboard.html", context)
