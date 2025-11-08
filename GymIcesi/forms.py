from django import forms
from .models import User, Employee

class TrainerAssaignForm(forms.form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label="Usuario")
    trainer = forms.ModelChoiceField(queryset=Employee.objects.none(), label="Entrenador")
    since = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date"}))
    until = forms.DateField(required=False, widget=forms.DateInput(attrs={"type":"date"}))

def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(is_active=True)
        self.fields["trainer"].queryset = Employee.objects.filter(employee_type__name="TRAINER")