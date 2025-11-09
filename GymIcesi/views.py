from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from GymIcesi.models import Student, Employee
from .models import User as UniUser 
from . import mongo_utils
    

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