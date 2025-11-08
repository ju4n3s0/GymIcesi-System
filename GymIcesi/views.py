

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login








def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')  
        password = request.POST.get('password')
        print("DEBUG: Intentando autenticar al usuario:", username)
        user = authenticate(request, username=username, password=password)

        if user is not None:
            user.refresh_from_db()

            if user.is_superuser:
                print("DEBUG: El usuario es superusuario.")
                messages.error(request, "El superusuario solo puede acceder al admin.")
                return redirect('login')

            print("DEBUG: Login exitoso.")
            login(request, user)
            return redirect('carreerFilter')

        else:
            print("DEBUG: Falló la autenticación para el usuario:", username)
            messages.error(request, "La contraseña o el usuario son incorrectos.")
    
    return render(request, 'registration/login.html')


def printReports(request):
    print("while")
    