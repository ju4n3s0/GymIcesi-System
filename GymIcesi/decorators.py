from functools import wraps
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if getattr(user, "role", None) in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponseForbidden("No tienes permisos para acceder a esta vista.")
        return _wrapped
    return decorator
