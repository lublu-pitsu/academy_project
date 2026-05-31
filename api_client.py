import os
from dotenv import load_dotenv
import requests
import urllib3
import uuid

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class EmulatorAPI:
    BASE_URL = os.getenv('API_URL')
    API_KEY = os.getenv('API_KEY')

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

    def get_app_me(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_disciplines(self):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/disciplines')

    def get_groups(self):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/groups')

    def get_students(self, **filters):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/students', params=filters)

    def get_teachers(self, **filters):
        teachers = self._get_all_pages(f'{self.BASE_URL}/api/v1/teachers', params=filters)
        # Собираем полное имя
        for t in teachers:
            parts = [t.get('last_name', ''), t.get('first_name', ''), t.get('middle_name', '')]
            t['full_name'] = ' '.join(parts).strip()
        return teachers

    def get_accounts(self, **filters):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/accounts', params=filters)

    def get_debts(self, **filters):
        return self._get_all_pages(f'{self.BASE_URL}/api/v1/debts', params=filters)

    def get_my_debts(self, access_token):
    # Пробуем сначала пользовательский API
        url = f'{self.BASE_URL}/api/v1/app/me/debts'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
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

    def get_teacher_debts(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/teacher/debts'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'data' in data:
            return data['data']
        return []

    def grade_debt(self, debt_id, grade, comment, access_token):
        url = f'{self.BASE_URL}/api/v1/app/teacher/debts/{debt_id}/grade'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        payload = {
            'grade': grade,
            'comment': comment or '',
            'idempotency_key': str(uuid.uuid4())
        }
        r = requests.post(url, headers=headers, json=payload, verify=False, timeout=10)
        r.raise_for_status()
        return r.json()

    def get_dean_summary_debts(self, access_token):
        url = f'{self.BASE_URL}/api/v1/app/dean/summary/debts'
        headers = {'Authorization': f'Bearer {access_token}'}
        r = requests.get(url, headers=headers, verify=False, timeout=10)
        r.raise_for_status()
        return r.json()

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