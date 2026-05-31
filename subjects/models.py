from django.db import models
from django.contrib.auth.models import User
from accounts.models import Profile

class StudentGroup(models.Model):
    number = models.CharField('Номер группы', max_length=10, unique=True)

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self):
        return self.number


class Subject(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    teachers = models.ManyToManyField(
        User,
        limit_choices_to={'profile__role': 'teacher'},
        related_name='subjects_taught',
        verbose_name='Преподаватели'
    )
    groups = models.ManyToManyField(
        StudentGroup,
        related_name='subjects',
        verbose_name='Группы'
    )

    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'

    def __str__(self):
        return self.name
    

class Enrollment(models.Model):
    class Status(models.TextChoices):
        PASSED = 'passed', 'Зачтено / Сдано'
        FAILED = 'failed', 'Задолженность'
        IN_PROGRESS = 'in_progress', 'В процессе'

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'profile__role': 'student'},
        related_name='enrollments'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='enrollments'
    )
    grade = models.CharField('Оценка / Зачёт', max_length=10, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
        verbose_name='Статус'
    )
    date_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'subject')    # Деканат
        verbose_name = 'Запись успеваемости'
        verbose_name_plural = 'Записи успеваемости'

    def __str__(self):
        return f'{self.student.profile.full_name()} - {self.subject.name}'