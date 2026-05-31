from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    ROLE_CHOICES = (
        ('student', 'Студент'),
        ('teacher', 'Преподаватель'),
        ('dean', 'Деканат'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    patronymic = models.CharField('Отчество', max_length=60, blank=True, default='') 
    phone = models.CharField('Телефон', max_length=20, blank=True, default='') 
    role = models.CharField('Роль', max_length=10, choices=ROLE_CHOICES, default='student')
    
    student_id = models.CharField(max_length=100, null=True, blank=True) 
    teacher_id = models.CharField(max_length=100, null=True, blank=True)  

    def full_name(self):
        initials = ''
        if self.user.first_name and self.patronymic:
            initials = f'{self.user.first_name[0]}.{self.patronymic[0]}.'
        return f'{self.user.last_name} {initials}'.strip()

    def __str__(self):
        return f'{self.user.get_full_name()} ({self.get_role_display()})'