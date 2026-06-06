import requests
import urllib3
import uuid
import json
from django.conf import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EmulatorAPI:
    BASE_URL = settings.EMULATOR_BASE_URL
    API_KEY = settings.EMULATOR_API_KEY

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'X-API-Key': self.API_KEY})
        self.session.verify = False

    def login(self, email, password):
        url = f'{self.BASE_URL}/api/v1/auth/login'
        payload = {'email': email, 'password': password}
        r = self.session.post(url, json=payload, timeout=10)
        r.raise_for_status()
        return r.json()

    def refresh_access_token(self, refresh_token):
        url = f'{self.BASE_URL}/api/v1/auth/refresh'
        payload = {'refresh_token': refresh_token}
        r = self.session.post(url, json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get('access_token'), data.get('refresh_token', refresh_token)

    def _user_api_request(self, method, url, access_token, refresh_token=None, **kwargs):
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {access_token}'
        r = self.session.request(method, url, headers=headers, **kwargs)
        if r.status_code == 401 and refresh_token:
            new_access, new_refresh = self.refresh_access_token(refresh_token)
            if new_access:
                headers['Authorization'] = f'Bearer {new_access}'
                r = self.session.request(method, url, headers=headers, **kwargs)
                return r, new_access, new_refresh
        return r, access_token, refresh_token

    def get_app_me(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_my_notifications(self, access_token):
        """Получить уведомления текущего пользователя."""
        url = f'{self.BASE_URL}/api/v1/app/me/notifications'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        return []

    def get_disciplines(self):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/disciplines')

    def get_groups(self):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/groups')

    def get_students(self, **filters):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/students', params=filters)

    def get_teachers(self, **filters):
        teachers = self._get_all_pages(f'{self.BASE_URL}/api/v1/teachers', params=filters)
        for t in teachers:
            parts = [t.get('last_name', ''), t.get('first_name', ''), t.get('middle_name', '')]
            t['full_name'] = ' '.join(parts).strip()
        return teachers

    def get_accounts(self, **filters):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/accounts', params=filters)

    def get_debts(self, **filters):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/debts', params=filters)

    def get_debts_for_discipline(self, discipline_id):
        all_debts = self._get_all_pages(
            f'{self.BASE_URL}/api/v1/debts',
            params={'discipline_id': discipline_id}
        )
        return [d for d in all_debts if d.get('status') in ('open', 'in_progress')]

    def get_my_debts(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/me/debts'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and 'data' in data:
            items = data['data']
        else:
            items = []
        if not items:
            me = self.get_app_me(access_token)
            student_id = me.get('linked_entity_id')
            if student_id:
                all_debts = self.get_debts(student_id=student_id)
                return all_debts
        return items

    def get_teacher_debts(self, access_token, refresh_token=None):
        url = f'{self.BASE_URL}/api/v1/app/teacher/debts'
        r, new_access, new_refresh = self._user_api_request('GET', url, access_token, refresh_token)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data, new_access, new_refresh
        elif isinstance(data, dict) and 'data' in data:
            return data['data'], new_access, new_refresh
        return [], new_access, new_refresh

    def grade_debt(self, debt_id, grade, grade_type, comment, access_token, refresh_token=None):
        url = f'{self.BASE_URL}/api/v1/app/teacher/debts/{debt_id}/grade'
        if grade_type == 'numeric':
            payload = {
                'grade': {'type': 'numeric', 'value': int(grade)},
                'comment': comment or '',
                'idempotency_key': str(uuid.uuid4())
            }
        else:
            payload = {
                'grade': {'type': 'pass_fail', 'value': grade},
                'comment': comment or '',
                'idempotency_key': str(uuid.uuid4())
            }
        r, new_access, new_refresh = self._user_api_request('POST', url, access_token, refresh_token, json=payload)
        r.raise_for_status()
        return r.json(), new_access, new_refresh

    def get_dean_summary_debts(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/summary/debts'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_student_retakes(self, access_token, refresh_token=None):
        url = f'{self.BASE_URL}/api/v1/app/me/retakes'
        r, new_access, new_refresh = self._user_api_request('GET', url, access_token, refresh_token)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and 'data' in data:
            items = data['data']
        else:
            items = []
        return items, new_access, new_refresh

    def get_teacher_retakes(self, access_token, refresh_token=None):
        url = f'{self.BASE_URL}/api/v1/app/teacher/retakes'
        r, new_access, new_refresh = self._user_api_request('GET', url, access_token, refresh_token)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and 'data' in data:
            items = data['data']
        else:
            items = []
        return items, new_access, new_refresh

    def create_dean_retake(self, data, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/retakes'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        r = self.session.post(url, json=data, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_dean_summary_retakes(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/summary/retakes'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_dean_retake_requests(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/retake-requests'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def review_retake_request(self, request_id, decision, review_comment, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/retake-requests/{request_id}/review'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        payload = {'decision': decision, 'review_comment': review_comment}
        r = self.session.patch(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json()

    def create_teacher_retake_request(self, data, access_token, refresh_token=None):
        url = f'{self.BASE_URL}/api/v1/app/teacher/retake-requests'
        r, new_access, new_refresh = self._user_api_request('POST', url, access_token, refresh_token, json=data)
        r.raise_for_status()
        return r.json(), new_access, new_refresh

    def export_retakes_csv(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/export/retakes.csv'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = self.session.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.text

    def _get_all_pages(self, url, params=None):
        if params is None:
            params = {}
        params['page'] = 1
        params['limit'] = 500
        items = []
        while True:
            r = self.session.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            if 'data' in data:
                items.extend(data['data'])
                total = data.get('meta', {}).get('total', 0)
                if len(items) >= total:
                    break
            elif isinstance(data, list):
                items.extend(data)
                break
            else:
                break
            params['page'] += 1
            if params['page'] > 100:
                break
        return items