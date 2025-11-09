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
from . import views 
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

from .views import login_user

from django.urls import include
from django.contrib.auth import views as auth_views
from .views import exercise_list, routine_list, routine_create 
from django.views.generic import RedirectView
from GymIcesi.forms import InstitutionalAuthenticationForm

from .views import assignment_show, assignment_quick
urlpatterns = [
    path("", RedirectView.as_view(pattern_name="accounts_login", permanent=False)),

    path("admin/", admin.site.urls),

    #Auth
    path("accounts/login/", auth_views.LoginView.as_view(template_name="accounts/login.html", authentication_form=InstitutionalAuthenticationForm,), name="accounts_login",),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="accounts_logout"),

    path('', lambda request: redirect('accounts/login', permanent=False)),
    path('admin/', admin.site.urls),
     # Ejercicios
    path("workouts/exercises/", views.exercise_list, name="exercise_list"),

    # Rutinas
    path("workouts/routines/", views.routine_list, name="routine_list"),
    path("workouts/routines/new/", views.routine_create, name="routine_create"),



    path("workouts/assign/", views.routine_assign, name="routine_assign"),

    # 📌 Progreso
    path("progress/", views.progress_list, name="progress_list"),
    path("progress/new/", views.progress_create, name="progress_create"),
    
    path('assigment/', assignment_show, name="assignment_show"),
    path('assigment/quick-assign/', assignment_quick, name = "assignment_quick"),
    
    path("workouts/users/", views.routine_users, name="routine_users"),
    path("workouts/users/<str:user_pk>/routines/",views.user_routine_history,name="user_routine_history"),
    
    
    path("reports/", views.reports_home, name="reports_home"),
    path("reports/users/", views.report_user_assignments, name="report_user_assignments"),
    path("reports/users/without/", views.report_users_without_routines, name="report_users_without_routines"),
    path("reports/exercises/top/", views.report_top_exercises, name="report_top_exercises"),
]

if settings.DEBUG:
    urlpatterns += static('/css/', document_root=os.path.join(settings.BASE_DIR, 'GymIcesi/templates'))
    urlpatterns += static('/html/', document_root=os.path.join(settings.BASE_DIR, 'GymIcesi/templates'))

