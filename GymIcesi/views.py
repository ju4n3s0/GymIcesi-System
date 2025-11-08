# GymIcesi/views.py

from django.utils import timezone
from django.utils.text import slugify
from bson import ObjectId
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages

from .forms import ExerciseForm, RoutineForm, TrainerAssignForm
from .models import User, Employee
from . import mongo_utils


def staff_required(u):
    return u.is_authenticated and (u.is_staff or u.is_superuser)


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


from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login








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


def printReports(request):
    print("while")
    