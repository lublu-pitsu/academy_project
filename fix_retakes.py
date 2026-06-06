from retakes.models import Retake
from api_client import EmulatorAPI

api = EmulatorAPI()
teachers = api.get_teachers()
teacher_map = {t['id']: f"{t.get('last_name', '')} {t.get('first_name', '')} {t.get('middle_name', '')}".strip() for t in teachers}

updated = 0
for retake in Retake.objects.all():
    new_teachers = []
    changed = False
    for teacher in retake.teachers:
        if len(teacher) == 36 and '-' in teacher and teacher in teacher_map:
            new_teachers.append(teacher_map[teacher])
            changed = True
        else:
            new_teachers.append(teacher)
    if changed:
        retake.teachers = new_teachers
        retake.save()
        updated += 1
        print(f"Исправлена: {retake.discipline_name}")
print(f"Обновлено: {updated}")