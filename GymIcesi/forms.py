from django import forms
from .models import User, Employee

class TrainerAssaignForm(forms.form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Usuario (STUDENT)")
    trainer = forms.ModelChoiceField(queryset=Employee.objects.none(), label="Entrenador (EMPLOYEE)")
    since = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date"}))
    until = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo users activos de rol STUDENT
        self.fields["user"].queryset = User.objects.filter(is_active=True, role="STUDENT")
        # Solo users activos de rol EMPLOYEE (desde aquí obtendremos el Employee.id)
        self.fields["trainer_user"].queryset = User.objects.filter(is_active=True, role="EMPLOYEE")

    def clean(self):
        cleaned = super().clean()
        trainer_user = cleaned.get("trainer_user")
        # Asegúrate que el EMPLOYEE tenga FK a Employee (por si hay datos incompletos)
        if trainer_user and trainer_user.employee_id is None:
            raise forms.ValidationError("El entrenador seleccionado no tiene un empleado asociado.")
        return cleaned