from django.contrib.auth import get_user_model
from django.db import transaction
from GymIcesi.models import (
    User as InstitutionalUser,  # tabla USERS (managed=False)
    Student,
    Employee
)
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend

User = get_user_model()

ROLE_FLAGS = {
    "STUDENT":  {"is_staff": False, "is_superuser": False},
    "EMPLOYEE": {"is_staff": True,  "is_superuser": False},
    "ADMIN":    {"is_staff": True,  "is_superuser": True},
}

def verify_institutional_password(raw_password: str, stored_hash: str) -> bool:
    # --- deja tu verificador como lo teníamos (sha256::..., django::..., o texto plano) ---
    if not stored_hash:
        return False
    stored = stored_hash.strip()
    import re, hashlib
    from django.contrib.auth.hashers import check_password
    if stored.startswith("django::"):
        return check_password(raw_password, stored.split("django::", 1)[1])
    if stored.startswith("sha256::"):
        hexd = stored.split("sha256::", 1)[1]
        return hashlib.sha256(raw_password.encode("utf-8")).hexdigest() == hexd
    if re.match(r"^(pbkdf2_|bcrypt\$|argon2\$)", stored):
        return check_password(raw_password, stored)
    # fallback: texto plano (útil si tus datos son de prueba tipo 'hash_lh123')
    return raw_password == stored

class InstitutionalBackend(BaseBackend):  # ← hereda de BaseBackend
    def authenticate(self, request, email=None, username=None, password=None, **kwargs):
        if not password:
            print("[AUTH] password vacío")
            return None

        email_val = email or username
        if not email_val:
            print("[AUTH] sin email/username")
            return None

        # 1) buscar por email en STUDENTS o EMPLOYEES
        link = {}
        try:
            stu = Student.objects.get(email=email_val)
            link["student_id"] = stu.id
            print(f"[AUTH] email pertenece a STUDENT id={stu.id}")
        except Student.DoesNotExist:
            try:
                emp = Employee.objects.get(email=email_val)
                link["employee_id"] = emp.id
                print(f"[AUTH] email pertenece a EMPLOYEE id={emp.id}")
            except Employee.DoesNotExist:
                print("[AUTH] email no existe en STUDENTS/EMPLOYEES")
                return None

        # 2) USERS institucional
        try:
            inst_user = InstitutionalUser.objects.get(**link)
        except InstitutionalUser.DoesNotExist:
            print(f"[AUTH] USERS no tiene fila para {link}")
            return None

        if not getattr(inst_user, "is_active", True):
            print("[AUTH] USERS.is_active = False")
            return None

        # 3) validar contraseña
        ok = verify_institutional_password(password, getattr(inst_user, "password_hash", ""))
        if not ok:
            print(f"[AUTH] password inválido para username={getattr(inst_user, 'username', email_val)}")
            return None

        role = getattr(inst_user, "role", "STUDENT")
        flags = ROLE_FLAGS.get(role, {"is_staff": False, "is_superuser": False})
        username_val = getattr(inst_user, "username", email_val)

        # 4) reflejar AuthUser (sin password usable)
        User = get_user_model()
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=username_val,
                defaults={
                    "email": email_val,
                    "role": role,
                    "student_id": getattr(inst_user, "student_id", None),
                    "employee_id": getattr(inst_user, "employee_id", None),
                    "is_active": getattr(inst_user, "is_active", True),
                    **flags,
                },
            )
            changed = False
            for k, v in {
                "email": email_val,
                "role": role,
                "student_id": getattr(inst_user, "student_id", None),
                "employee_id": getattr(inst_user, "employee_id", None),
                "is_active": getattr(inst_user, "is_active", True),
                **flags,
            }.items():
                if getattr(user, k) != v:
                    setattr(user, k, v)
                    changed = True
            if user.has_usable_password():
                user.set_unusable_password()
                changed = True
            if changed:
                user.save()

        print(f"[AUTH] OK -> {user.username} ({user.role})")
        return user

    def get_user(self, user_id):
        """
        Necesario para que el middleware reconstruya request.user desde la sesión.
        """
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None