from django.core.management.base import BaseCommand
from subjects.models import Subject, StudentGroup, Enrollment
from django.contrib.auth.models import User
from accounts.models import Profile
import random

class Command(BaseCommand):
    help = 'Создаёт демонстрационные предметы и записи'

    def handle(self, *args, **options):
        # Создаём группы, если ещё нет
        groups = ['ПИ31Б', 'ПИ32Б', 'ИВТ41А', 'ИСТ21В', 'ПМИ11Г']
        group_objs = []
        for g in groups:
            obj, _ = StudentGroup.objects.get_or_create(number=g)
            group_objs.append(obj)

        # Получаем преподавателей
        teachers = User.objects.filter(profile__role='teacher')
        if not teachers.exists():
            self.stdout.write(self.style.ERROR('Нет преподавателей. Сначала выполните populate_db'))
            return

        # Создаём предметы
        subjects_data = [
            ('Математический анализ', 'Мат. анализ для 1-2 курсов', ['ПИ31Б', 'ПИ32Б']),
            ('Программирование', 'Основы Python', ['ПИ31Б', 'ИВТ41А']),
            ('Базы данных', 'SQL и проектирование', ['ИВТ41А', 'ПМИ11Г']),
            ('Физика', 'Общая физика', ['ИСТ21В']),
            ('Английский язык', 'Технический английский', ['ПИ31Б', 'ПИ32Б', 'ИВТ41А']),
        ]
        for name, desc, group_list in subjects_data:
            subject = Subject.objects.create(name=name, description=desc)
            # Назначаем случайных 1-2 преподавателей
            subject.teachers.set(random.sample(list(teachers), k=min(2, len(teachers))))
            # Добавляем группы
            for gn in group_list:
                group_obj = StudentGroup.objects.get(number=gn)
                subject.groups.add(group_obj)
            # Создаём Enrollment для студентов этих групп
            for group_obj in subject.groups.all():
                students_in_group = User.objects.filter(
                    profile__role='student',
                    profile__group_number=group_obj.number
                )
                for student in students_in_group:
                    Enrollment.objects.get_or_create(
                        student=student,
                        subject=subject,
                        defaults={'status': random.choice(['in_progress', 'passed', 'failed']),
                                  'grade': random.choice(['5', '4', '3', 'Зачёт', ''])}
                    )
            self.stdout.write(f'Предмет "{name}" создан')
        self.stdout.write(self.style.SUCCESS('Демо-предметы успешно созданы!'))