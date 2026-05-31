from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import Profile

class Command(BaseCommand):
    help = 'Создаёт профили для пользователей, у которых их нет'

    def handle(self, *args, **options):
        users_without_profile = []
        for user in User.objects.all():
            profile, created = Profile.objects.get_or_create(user=user)
            if created:
                users_without_profile.append(user.username)
        
        if users_without_profile:
            self.stdout.write(
                self.style.SUCCESS(f'Созданы профили для пользователей: {", ".join(users_without_profile)}')
            )
        else:
            self.stdout.write(self.style.SUCCESS('У всех пользователей уже есть профили!'))