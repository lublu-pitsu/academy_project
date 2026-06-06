from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from .models import Profile
from api_client import EmulatorAPI
import traceback

class EmulatorBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        if not username or not password:
            return None

        try:
            api = EmulatorAPI()
            tokens = api.login(username, password)
            access_token = tokens.get('access_token')
            if not access_token:
                return None

            me = api.get_app_me(access_token)
            email = me.get('email', username)
            role = me.get('role', 'student')

            user, created = User.objects.get_or_create(
                username=email,
                defaults={
                    'email': email,
                    'first_name': me.get('first_name', ''),
                    'last_name': me.get('last_name', ''),
                }
            )
            if not created:
                user.email = email
                user.first_name = me.get('first_name', '')
                user.last_name = me.get('last_name', '')
                user.save()

            profile, _ = Profile.objects.get_or_create(user=user)
            role_map = {
                'student': 'student',
                'teacher': 'teacher',
                'dean': 'dean',
                'dean_office': 'dean',
            }
            profile.role = role_map.get(role, 'student')
            profile.patronymic = me.get('middle_name') or ''
            profile.phone = me.get('phone') or ''

            linked_entity_id = me.get('linked_entity_id')
            linked_entity_type = me.get('linked_entity_type')
            if linked_entity_type == 'teacher':
                profile.teacher_id = str(linked_entity_id) if linked_entity_id else None
            elif linked_entity_type == 'student':
                profile.student_id = str(linked_entity_id) if linked_entity_id else None

            profile.save()

            if request and hasattr(request, 'session'):
                request.session['access_token'] = access_token
                request.session['refresh_token'] = tokens.get('refresh_token', '')
                request.session.save()

            return user

        except Exception as e:
            print(f"[AUTH ERROR] {e}")
            traceback.print_exc()
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None