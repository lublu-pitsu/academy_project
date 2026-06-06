import json
from collections import OrderedDict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from api_client import EmulatorAPI
from accounts.models import Profile
from django.http import JsonResponse

def is_dean(user):
    return hasattr(user, 'profile') and user.profile.role == 'dean'

def is_teacher(user):
    return hasattr(user, 'profile') and user.profile.role == 'teacher'

def is_student(user):
    return hasattr(user, 'profile') and user.profile.role == 'student'


@login_required
@user_passes_test(is_dean)
def subject_list(request):
    api = EmulatorAPI()
    try:
        disciplines = api.get_disciplines()
    except Exception as e:
        print(f"Error loading disciplines: {e}")
        disciplines = []
    return render(request, 'subjects/subject_list.html', {'subjects': disciplines})


@login_required
@user_passes_test(is_teacher)
def teacher_subjects(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return render(request, 'subjects/teacher_subjects.html', {'subjects': [], 'error': 'Нет доступа'})

    api = EmulatorAPI()
    try:
        me = api.get_app_me(access_token)
        teacher_id = me.get('linked_entity_id')

        all_debts = api.get_debts()
        teacher_debts = [d for d in all_debts if d.get('teacher_id') == teacher_id]

        all_disc = api.get_disciplines()
        disc_ids = {d.get('discipline_id') for d in teacher_debts}
        teacher_discs = [d for d in all_disc if d['id'] in disc_ids]

    except Exception as e:
        print(f"Error loading teacher subjects: {e}")
        return render(request, 'subjects/teacher_subjects.html', {'subjects': [], 'error': str(e)})

    return render(request, 'subjects/teacher_subjects.html', {'subjects': teacher_discs})


@login_required
@user_passes_test(is_teacher)
def subject_students(request, subject_pk):
    discipline_id = str(subject_pk)
    access_token = request.session.get('access_token')
    if not access_token:
        return render(request, 'subjects/subject_students.html', {
            'subject': {'id': discipline_id, 'name': 'Дисциплина'},
            'enrollments': [],
            'error': 'Нет доступа'
        })

    api = EmulatorAPI()
    try:
        me = api.get_app_me(access_token)
        teacher_id = me.get('linked_entity_id')

        all_debts = api.get_debts()
        debts_for_disc = [
            d for d in all_debts
            if d.get('teacher_id') == teacher_id and d.get('discipline_id') == discipline_id
        ]

        disciplines = api.get_disciplines()
        teachers = api.get_teachers()
        groups = api.get_groups()
        accounts = api.get_accounts(role='student')

    except Exception as e:
        print(f"Error loading subject students: {e}")
        return render(request, 'subjects/subject_students.html', {
            'subject': {'id': discipline_id, 'name': 'Дисциплина'},
            'enrollments': [],
            'error': str(e)
        })

    disc_map = {d['id']: d.get('name', '—') for d in disciplines}
    
    teacher_map = {}
    for t in teachers:
        parts = [t.get('last_name', ''), t.get('first_name', ''), t.get('middle_name', '')]
        teacher_map[t['id']] = ' '.join(parts).strip()
    
    group_map = {g['id']: g.get('name', '—') for g in groups}

    student_info = {}
    for acc in accounts:
        if acc.get('linked_entity_type') == 'student' and acc.get('linked_entity_id'):
            sid = acc['linked_entity_id']
            student_info[sid] = {
                'email': acc.get('email', '—'),
                'full_name': f"{acc.get('last_name', '')} {acc.get('first_name', '')} {acc.get('middle_name', '')}".strip(),
                'group_id': acc.get('group_id', None)
            }

    CONTROL_TYPES = {
        'exam': 'Экзамен',
        'credit': 'Зачёт',
        'differentiated_credit': 'Диф. зачёт',
        'coursework': 'Курсовая',
        'practice': 'Практика',
        'lab_work': 'Лаб. работа',
        'other': 'Другое',
    }

    DEBT_TYPES = {
        'failed_exam': 'Не сдан экзамен',
        'failed_credit': 'Не сдан зачёт',
        'not_attended': 'Неявка',
        'not_allowed': 'Не допущен',
        'coursework_not_submitted': 'Курсовая не сдана',
        'practice_not_completed': 'Практика не пройдена',
        'other': 'Другая причина',
    }

    STATUS_MAP = {
        'open': 'В процессе',
        'in_progress': 'В процессе',
        'passed': 'Зачтено / Сдано',
        'failed': 'Задолженность',
        'closed': 'Зачтено / Сдано',
    }

    subject_name = disc_map.get(discipline_id, 'Дисциплина')

    for debt in debts_for_disc:
        sid = debt.get('student_id')
        info = student_info.get(sid, {})
        
        debt['student_name'] = info.get('full_name') or '—'
        debt['student_email'] = info.get('email', '—')
        debt['group_name'] = group_map.get(info.get('group_id'), '—')
        debt['control_type_display'] = CONTROL_TYPES.get(debt.get('control_type', ''), debt.get('control_type', '—'))
        debt['debt_type_display'] = DEBT_TYPES.get(debt.get('debt_type', ''), debt.get('debt_type', '—'))
        debt['status_display'] = STATUS_MAP.get(debt.get('status', ''), '—')
        debt['semester_display'] = f"{debt.get('semester', '?')} семестр"

    return render(request, 'subjects/subject_students.html', {
        'subject': {'id': discipline_id, 'name': subject_name},
        'enrollments': debts_for_disc,
    })


@login_required
@user_passes_test(is_teacher)
def update_grade(request, enrollment_pk):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Метод не поддерживается'}, status=400)

    debt_id = str(enrollment_pk)
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    if not access_token:
        return JsonResponse({'status': 'error', 'error': 'Нет доступа'}, status=403)

    grade = request.POST.get('grade', '')
    grade_type = request.POST.get('grade_type', 'numeric')
    comment = request.POST.get('comment', '')

    api = EmulatorAPI()
    try:
        resp, new_access, new_refresh = api.grade_debt(debt_id, grade, grade_type, comment, access_token, refresh_token)

        if new_access and new_access != access_token:
            request.session['access_token'] = new_access
            request.session['refresh_token'] = new_refresh

        return JsonResponse({
            'status': 'ok',
            'grade': resp.get('grade', grade),
            'status_display': 'Зачтено / Сдано'
        })
    except Exception as e:
        print(f"Error grading debt: {e}")
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_student)
def my_subjects(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return render(request, 'subjects/my_subjects.html', {'grouped_enrollments': {}, 'error': 'Нет доступа'})

    api = EmulatorAPI()
    try:
        me = api.get_app_me(access_token)
        student_id = me.get('linked_entity_id')

        all_debts = api.get_debts()
        debts = [d for d in all_debts if d.get('student_id') == student_id]

        disciplines = api.get_disciplines()
        teachers = api.get_teachers()

    except Exception as e:
        print(f"Error loading my subjects: {e}")
        return render(request, 'subjects/my_subjects.html', {'grouped_enrollments': {}, 'error': str(e)})

    disc_map = {}
    for d in disciplines:
        disc_map[d['id']] = {
            'name': d.get('name', 'Без названия'),
            'code': d.get('code', ''),
            'department': d.get('department', '')
        }
    
    teacher_map = {}
    for t in teachers:
        parts = [t.get('last_name', ''), t.get('first_name', ''), t.get('middle_name', '')]
        teacher_map[t['id']] = {
            'full_name': ' '.join(parts).strip(),
            'department': t.get('department', '')
        }

    CONTROL_TYPES = {
        'exam': 'Экзамен',
        'credit': 'Зачёт',
        'differentiated_credit': 'Диф. зачёт',
        'coursework': 'Курсовая',
        'practice': 'Практика',
        'lab_work': 'Лаб. работа',
        'other': 'Другое',
    }

    DEBT_TYPES = {
        'failed_exam': 'Не сдан экзамен',
        'failed_credit': 'Не сдан зачёт',
        'not_attended': 'Неявка',
        'not_allowed': 'Не допущен',
        'coursework_not_submitted': 'Курсовая не сдана',
        'practice_not_completed': 'Практика не пройдена',
        'other': 'Другая причина',
    }

    STATUS_MAP = {
        'open': 'В процессе',
        'in_progress': 'В процессе',
        'passed': 'Зачтено / Сдано',
        'failed': 'Задолженность',
        'closed': 'Зачтено / Сдано',
    }

    for debt in debts:
        disc_id = debt.get('discipline_id')
        teacher_id = debt.get('teacher_id')
        
        disc_info = disc_map.get(disc_id, {})
        teacher_info = teacher_map.get(teacher_id, {})
        
        debt['discipline_name'] = disc_info.get('name', 'Неизвестная дисциплина')
        debt['discipline_code'] = disc_info.get('code', '')
        debt['department'] = disc_info.get('department', '')
        debt['teacher_name'] = teacher_info.get('full_name', 'Неизвестный преподаватель')
        debt['teacher_department'] = teacher_info.get('department', '')
        
        debt['control_type_display'] = CONTROL_TYPES.get(debt.get('control_type', ''), debt.get('control_type', '—'))
        debt['debt_type_display'] = DEBT_TYPES.get(debt.get('debt_type', ''), debt.get('debt_type', '—'))
        debt['semester_display'] = f"{debt.get('semester', '?')} семестр"
        debt['academic_year_display'] = debt.get('academic_year', '')
        debt['status_display'] = STATUS_MAP.get(debt.get('status', ''), debt.get('status', 'Неизвестно'))
        
        grade_raw = debt.get('grade')
        if grade_raw:
            if isinstance(grade_raw, str):
                try:
                    debt['grade'] = json.loads(grade_raw.replace("'", '"'))
                except (json.JSONDecodeError, ValueError):
                    debt['grade'] = {'type': 'pass_fail', 'value': grade_raw}
            elif isinstance(grade_raw, dict):
                debt['grade'] = grade_raw
        else:
            debt['grade'] = None

    grouped = OrderedDict()
    for debt in debts:
        disc_id = debt.get('discipline_id')
        if disc_id not in grouped:
            grouped[disc_id] = {
                'discipline_name': debt['discipline_name'],
                'discipline_code': debt['discipline_code'],
                'department': debt['department'],
                'teacher_name': debt['teacher_name'],
                'teacher_department': debt['teacher_department'],
                'debts': [],
                'active_count': 0,
            }
        grouped[disc_id]['debts'].append(debt)
        if debt.get('status') not in ('passed', 'closed'):
            grouped[disc_id]['active_count'] += 1

    grouped = OrderedDict(
        (k, v) for k, v in grouped.items() if v['active_count'] > 0
    )

    return render(request, 'subjects/my_subjects.html', {'grouped_enrollments': grouped})


@login_required
@user_passes_test(is_dean)
def group_list(request):
    api = EmulatorAPI()
    try:
        groups = api.get_groups()
    except Exception as e:
        print(f"Error loading groups: {e}")
        groups = []
    return render(request, 'subjects/group_list.html', {'groups': groups})


@login_required
@user_passes_test(is_dean)
def teachers_by_discipline(request):
    discipline_id = request.GET.get('discipline_id')
    if not discipline_id:
        return JsonResponse({'error': 'discipline_id required'}, status=400)
    api = EmulatorAPI()
    try:
        debts = api.get_debts(discipline_id=discipline_id)
        teacher_ids = set(d.get('teacher_id') for d in debts if d.get('teacher_id'))
        all_teachers = api.get_teachers()
        teachers = []
        for t in all_teachers:
            if t.get('id') in teacher_ids:
                full_name = ' '.join([t.get('last_name',''), t.get('first_name',''), t.get('middle_name','')]).strip()
                teachers.append({
                    'id': t['id'],
                    'full_name': full_name or t.get('email', 'Без имени')
                })
        return JsonResponse({'teachers': teachers})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def all_teachers(request):
    """Возвращает список всех преподавателей для выбора в форме"""
    api = EmulatorAPI()
    try:
        teachers = api.get_teachers()
        result = []
        for t in teachers:
            full_name = f"{t.get('last_name', '')} {t.get('first_name', '')} {t.get('middle_name', '')}".strip()
            result.append({
                'id': t['id'],
                'full_name': full_name or t.get('email', 'Без имени')
            })
        return JsonResponse({'teachers': result})
    except Exception as e:
        return JsonResponse({'teachers': [], 'error': str(e)}, status=500)