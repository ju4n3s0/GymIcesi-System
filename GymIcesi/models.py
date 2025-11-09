# university/models.py
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import AbstractUser
from django.db import models as dj_models


# --- Tablas catálogo simples ---

class Country(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)

    class Meta:
        db_table = "countries"
        managed = False

    def __str__(self):
        return self.name


class Department(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    country = models.ForeignKey(
        Country, db_column="country_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "departments"
        managed = False

    def __str__(self):
        return self.name


class City(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    department = models.ForeignKey(
        Department, db_column="dept_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "cities"
        managed = False

    def __str__(self):
        return self.name


class Campus(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20, blank=True, null=True)
    city = models.ForeignKey(
        City, db_column="city_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "campuses"
        managed = False

    def __str__(self):
        return self.name or f"Campus {self.code}"


class ContractType(models.Model):
    name = models.CharField(primary_key=True, max_length=30)

    class Meta:
        db_table = "contract_types"
        managed = False

    def __str__(self):
        return self.name


class EmployeeType(models.Model):
    name = models.CharField(primary_key=True, max_length=30)

    class Meta:
        db_table = "employee_types"
        managed = False

    def __str__(self):
        return self.name


# --- Núcleo académico ---

class Faculty(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=40)
    location = models.CharField(max_length=15)
    phone_number = models.CharField(max_length=15)
    # dean_id es único en SQL: lo modelamos como OneToOne opcional hacia Employee (definida más abajo)
    # Usamos string para referencia adelantada.
    dean = models.OneToOneField(
        "Employee", db_column="dean_id", to_field="id",
        on_delete=models.SET_NULL, null=True, blank=True, unique=True, related_name="+",
    )

    class Meta:
        db_table = "faculties"
        managed = False

    def __str__(self):
        return self.name


class Employee(models.Model):
    id = models.CharField(primary_key=True, max_length=15)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.CharField(max_length=30)
    contract_type = models.ForeignKey(
        ContractType, db_column="contract_type", to_field="name", on_delete=models.PROTECT
    )
    employee_type = models.ForeignKey(
        EmployeeType, db_column="employee_type", to_field="name", on_delete=models.PROTECT
    )
    faculty = models.ForeignKey(
        Faculty, db_column="faculty_code", to_field="code", on_delete=models.PROTECT
    )
    campus = models.ForeignKey(
        Campus, db_column="campus_code", to_field="code", on_delete=models.PROTECT
    )
    birth_place = models.ForeignKey(
        City, db_column="birth_place_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "employees"
        managed = False

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Area(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    faculty = models.ForeignKey(
        Faculty, db_column="faculty_code", to_field="code", on_delete=models.PROTECT
    )
    # coordinator_id tiene índice único: lo modelamos como OneToOne
    coordinator = models.OneToOneField(
        Employee, db_column="coordinator_id", to_field="id", on_delete=models.PROTECT, unique=True, related_name="+",
    )

    class Meta:
        db_table = "areas"
        managed = False

    def __str__(self):
        return self.name


class Program(models.Model):
    code = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=40)
    area = models.ForeignKey(
        Area, db_column="area_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "programs"
        managed = False

    def __str__(self):
        return self.name


class Subject(models.Model):
    code = models.CharField(primary_key=True, max_length=10)
    name = models.CharField(max_length=30)
    program = models.ForeignKey(
        Program, db_column="program_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "subjects"
        managed = False

    def __str__(self):
        return self.name


class Group(models.Model):
    nrc = models.CharField(primary_key=True, max_length=10, db_column="nrc")
    number = models.IntegerField()
    semester = models.CharField(max_length=6)
    subject = models.ForeignKey(
        Subject, db_column="subject_code", to_field="code", on_delete=models.PROTECT
    )
    professor = models.ForeignKey(
        Employee, db_column="professor_id", to_field="id", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "groups"
        managed = False

    def __str__(self):
        return f"{self.nrc} - {self.subject.name}"


class Student(models.Model):
    id = models.CharField(primary_key=True, max_length=15)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.CharField(max_length=50)
    birth_date = models.DateField()
    birth_place = models.ForeignKey(
        City, db_column="birth_place_code", to_field="code", on_delete=models.PROTECT
    )
    campus = models.ForeignKey(
        Campus, db_column="campus_code", to_field="code", on_delete=models.PROTECT
    )

    class Meta:
        db_table = "students"
        managed = False

    def __str__(self):
        return f"{self.id} - {self.first_name} {self.last_name}"


class Enrollment(models.Model):
    id = models.BigAutoField(primary_key=True)
    student = models.ForeignKey(Student, db_column="student_id", to_field="id", on_delete=models.CASCADE)
    group = models.ForeignKey(Group, db_column="NRC", to_field="nrc", on_delete=models.CASCADE)
    enrollment_date = models.DateField()
    status = models.CharField(max_length=15)

    class Meta:
        db_table = "enrollments"
        managed = False
        constraints = [
            models.UniqueConstraint(fields=["student", "group"], name="uq_enrollments_student_nrc")
        ]


class User(models.Model):
    username = models.CharField(primary_key=True, max_length=30)
    password_hash = models.CharField(max_length=100)
    role = models.CharField(max_length=20)  # STUDENT | EMPLOYEE | ADMIN
    student = models.ForeignKey(
        Student, db_column="student_id", to_field="id",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    employee = models.ForeignKey(
        Employee, db_column="employee_id", to_field="id",
        on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "users"
        constraints = [
            models.CheckConstraint(
                check=(
                    (Q(student__isnull=False) & Q(employee__isnull=True)) |
                    (Q(student__isnull=True) & Q(employee__isnull=False))
                ),
                name="users_one_role_chk"
            )
        ]

    def __str__(self):
        return self.username


# --- AUTENTICACIÓN DJANGO (modelo gestionado por Django) ---

class AuthUser(AbstractUser):
    class Role(dj_models.TextChoices):
        STUDENT = "STUDENT", "Student"
        EMPLOYEE = "EMPLOYEE", "Employee"
        ADMIN    = "ADMIN", "Admin"

    role = dj_models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    # en tu esquema, los IDs son texto; usa CharField
    student_id  = dj_models.CharField(max_length=15, null=True, blank=True)
    employee_id = dj_models.CharField(max_length=15, null=True, blank=True)

    def is_student(self):  return self.role == self.Role.STUDENT
    def is_employee(self): return self.role == self.Role.EMPLOYEE
    def is_admin(self):    return self.role == self.Role.ADMIN
    
    
    
