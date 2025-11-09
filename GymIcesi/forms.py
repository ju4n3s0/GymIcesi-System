# GymIcesi/forms.py
from django import forms
from .models import User, Employee

EXERCISE_TYPE_CHOICES = [
    ("cardio", "Cardio"),
    ("fuerza", "Fuerza"),
    ("movilidad", "Movilidad"),
]

DIFFICULTY_CHOICES = [
    ("baja", "Baja"),
    ("media", "Media"),
    ("alta", "Alta"),
]


class TrainerAssignForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Usuario"
    )
    trainer = forms.ModelChoiceField(
        queryset=Employee.objects.none(),
        label="Entrenador"
    )
    since = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )
    until = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Todos los usuarios activos de la tabla USERS (BD relacional)
        self.fields["user"].queryset = User.objects.filter(is_active=True)
        # Solo empleados con tipo "Instructor" (entrenadores)
        self.fields["trainer"].queryset = Employee.objects.filter(
            employee_type__name="Instructor"
        )


class ExerciseForm(forms.Form):
    name = forms.CharField(label="Nombre", max_length=100)
    type = forms.ChoiceField(label="Tipo", choices=EXERCISE_TYPE_CHOICES)
    description = forms.CharField(
        label="Descripción",
        widget=forms.Textarea,
        required=False
    )
    duration = forms.IntegerField(
        label="Duración (minutos)",
        min_value=1
    )
    difficulty = forms.ChoiceField(
        label="Dificultad",
        choices=DIFFICULTY_CHOICES
    )
    video_url = forms.URLField(
        label="Video demostrativo (URL)",
        required=False
    )


class RoutineForm(forms.Form):
    name = forms.CharField(
        label="Nombre de la rutina",
        max_length=100
    )
    description = forms.CharField(
        label="Descripción / objetivo",
        widget=forms.Textarea,
        required=False
    )
    exercises = forms.MultipleChoiceField(
        label="Ejercicios de la rutina",
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    def __init__(self, *args, **kwargs):
        from . import mongo_utils  # import aquí para evitar ciclos
        super().__init__(*args, **kwargs)
        db = mongo_utils.get_db()
        exercise_docs = db.exercises.find().sort("name", 1)
        self.fields["exercises"].choices = [
            (str(e["_id"]), f'{e["name"]} ({e["type"]})')
            for e in exercise_docs
        ]
        
        
class AssignRoutineForm(forms.Form):
    """
    Permite a un trainer asignar una rutina (Mongo) a cualquier usuario (SQL).
    """
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Usuario objetivo"
    )
    routine = forms.ChoiceField(
        label="Rutina",
        choices=(),  # se llena en __init__ desde Mongo
        widget=forms.RadioSelect
    )
    start_date = forms.DateField(
        label="Fecha de inicio",
        widget=forms.DateInput(attrs={"type": "date"})
    )
    notes = forms.CharField(
        label="Notas",
        widget=forms.Textarea,
        required=False
    )

    def __init__(self, *args, **kwargs):
        from . import mongo_utils  # evita ciclos
        super().__init__(*args, **kwargs)
        # Usuarios activos del SQL
        self.fields["user"].queryset = User.objects.filter(is_active=True)

        # Rutinas (Mongo)
        db = mongo_utils.get_db()
        routines = db.routines.find({"is_active": {"$ne": False}}).sort("name", 1)
        self.fields["routine"].choices = [
            (str(r["_id"]), r.get("name", "(sin nombre)"))
            for r in routines
        ]

