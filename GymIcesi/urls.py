"""
URL configuration for GymIcesi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from .views import login_user

from GymIcesi import views

urlpatterns = [
    path('', lambda request: redirect('login', permanent=False)),
    path('login/', login_user, name='login'),
    path('admin/', admin.site.urls),
     # Ejercicios
    path("workouts/exercises/", views.exercise_list, name="exercise_list"),

    # Rutinas
    path("workouts/routines/", views.routine_list, name="routine_list"),
    path("workouts/routines/new/", views.routine_create, name="routine_create"),
]

if settings.DEBUG:
    urlpatterns += static('/css/', document_root=os.path.join(settings.BASE_DIR, 'GymIcesi/templates'))
    urlpatterns += static('/html/', document_root=os.path.join(settings.BASE_DIR, 'GymIcesi/templates'))
