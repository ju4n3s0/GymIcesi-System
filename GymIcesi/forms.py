from django import forms
from .models import User

class TrainerAssignForm(forms.Form):
    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Usuario (STUDENT)"
    )
    trainer_user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        label="Entrenador (EMPLOYEE)"
    )
    since = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    until = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(is_active=True, role="STUDENT").order_by("username")
        self.fields["trainer_user"].queryset = (
            User.objects.filter(is_active=True, role="EMPLOYEE", employee__isnull=False)
                        .select_related("employee")
                        .order_by("employee__last_name", "employee__first_name")
        )

    def clean(self):
        cleaned = super().clean()
        tuser = cleaned.get("trainer_user")
        if tuser and tuser.employee_id is None:
            raise forms.ValidationError("El entrenador seleccionado no tiene Employee asociado (employee_id es NULL).")
        return cleaned