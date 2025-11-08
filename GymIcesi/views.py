from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from GymIcesi.models import Student, Employee
    

def assaignment_show(request):
    students = Student.objects.all()
    trainers = Employee.objects.all()
    return render(request, 'admin/assignment_list.html',{
        "students": students,
        "trainers":trainers,
        })