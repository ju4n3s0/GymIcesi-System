from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import TrainerAssignForm
from .models import User, Employee
from . import mongo_utils

def staff_required(u):
    return u.is_authenticated and (u.is_staff or u.is_superuser)

@login_required
def assaigment_list(request):
    