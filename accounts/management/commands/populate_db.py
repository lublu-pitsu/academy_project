from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile
from subjects.models import StudentGroup
from faker import Faker
import random

fake = Faker('ru_RU')

class Command(BaseCommand):
    help = 'Создаёт группы, 5 деканатов, 10 преподавателей и 100 студентов'

    def get_or_create_profile(self, user):
        try:
            return user.profile, False
        except Profile.DoesNotExist:
            return Profile.objects.create(user=user), True

    def handle(self, *args, **options):
        password = 'password123'
        created_count = 0
        updated_count = 0

        # 1. Создаём группы (объекты StudentGroup)
        group_numbers = ['ПИ31Б', 'ПИ32Б', 'ИВТ41А', 'ИСТ21В', 'ПМИ11Г', 'ПМИ21А']
        group_objs = {}
        for gn in group_numbers:
            obj, _ = StudentGroup.objects.get_or_create(number=gn)
            group_objs[gn] = obj
        self.stdout.write(f'Группы готовы: {list(group_objs.keys())}\n')

        # 2. Деканат (5)
        self.stdout.write('Создаю деканаты...')
        for i in range(1, 6):
            username = f'dean{i}'
            user, created = User.objects.get_or_create(username=username, defaults={
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'email': fake.email(),
            })
            if created:
                user.set_password(password)
                user.save()
            profile, _ = self.get_or_create_profile(user)
            profile.role = 'dean'
            profile.patronymic = fake.middle_name()
            profile.phone = fake.phone_number()
            profile.save()
            self.stdout.write(f'  ✓ dean{i}')

        # 3. Преподаватели (10)
        self.stdout.write('Создаю преподавателей...')
        for i in range(1, 11):
            username = f'teacher{i}'
            user, created = User.objects.get_or_create(username=username, defaults={
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'email': fake.email(),
            })
            if created:
                user.set_password(password)
                user.save()
            profile, _ = self.get_or_create_profile(user)
            profile.role = 'teacher'
            profile.patronymic = fake.middle_name()
            profile.phone = fake.phone_number()
            profile.save()
            self.stdout.write(f'  ✓ teacher{i}')

        # 4. Студенты (100) с привязкой к случайной группе из group_objs
        self.stdout.write('Создаю студентов...')
        group_list = list(group_objs.values())
        for i in range(1, 101):
            username = f'student{i}'
            user, created = User.objects.get_or_create(username=username, defaults={
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'email': fake.email(),
            })
            if created:
                user.set_password(password)
                user.save()
            profile, _ = self.get_or_create_profile(user)
            profile.role = 'student'
            profile.patronymic = fake.middle_name()
            profile.phone = fake.phone_number()
            profile.course = random.randint(1, 4)
            profile.group = random.choice(group_list)   # <-- теперь объект
            profile.save()
            if i % 20 == 0:
                self.stdout.write(f'  ✓ {i} студентов...')

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Готово! Пароль для всех: {password}'
        ))