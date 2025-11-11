# GymIcesi/forms.py
from django import forms

from GymIcesi import mongo_utils
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
        max_length=100,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    description = forms.CharField(
        label="Descripción",
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
    exercises = forms.MultipleChoiceField(
        label="Ejercicios de la rutina",
        choices=(),
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db = mongo_utils.get_db()
        exercises_cursor = db.exercises.find().sort("name", 1)

        choices = []
        for e in exercises_cursor:
            name = e.get("name", "Sin nombre")
            ex_type = e.get("type", "sin tipo")  # 👈 evita KeyError
            choices.append((str(e["_id"]), f"{name} ({ex_type})"))

        self.fields["exercises"].choices = choices

