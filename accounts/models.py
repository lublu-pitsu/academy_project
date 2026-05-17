from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    username = None

    email = models.EmailField('Email', unique=True)

    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('deanery', 'Деканат'),
        ('teacher', 'Преподаватель'),
        ('student', 'Студент'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='student', 
        verbose_name='Роль'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"