from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from api_client import EmulatorAPI
from accounts.models import Profile
from collections import OrderedDict
import csv
import io
from datetime import datetime
from urllib.parse import urlencode

def is_dean(user):
    try:
        return user.profile.role == 'dean'
    except Profile.DoesNotExist:
        return False


def get_all_data(api):
    """Получает все данные из API"""
    all_debts = api.get_debts()
    disciplines = api.get_disciplines()
    teachers = api.get_teachers()
    groups = api.get_groups()
    accounts = api.get_accounts()
    return all_debts, disciplines, teachers, groups, accounts


def enrich_debts(all_debts, disciplines, teachers, groups, accounts):
    """Обогащает долги данными"""
    disc_map = {d['id']: d for d in disciplines}
    
    teacher_map = {}
    for t in teachers:
        parts = [t.get('last_name', ''), t.get('first_name', ''), t.get('middle_name', '')]
        teacher_map[t['id']] = {
            'full_name': ' '.join(parts).strip(),
            'department': t.get('department', '')
        }
    
    group_map = {g['id']: g.get('name', '—') for g in groups}

    student_map = {}
    for acc in accounts:
        if acc.get('linked_entity_type') == 'student' and acc.get('linked_entity_id'):
            sid = acc['linked_entity_id']
            student_map[sid] = {
                'email': acc.get('email', '—'),
                'full_name': f"{acc.get('last_name', '')} {acc.get('first_name', '')} {acc.get('middle_name', '')}".strip(),
                'group_id': acc.get('group_id', None),
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
        'open': 'Открыт',
        'in_progress': 'В процессе',
        'passed': 'Сдано',
        'failed': 'Задолженность',
    }

    for debt in all_debts:
        disc_id = debt.get('discipline_id')
        disc = disc_map.get(disc_id, {})
        
        student_id = debt.get('student_id')
        student = student_map.get(student_id, {})
        
        teacher = teacher_map.get(debt.get('teacher_id'), {})
        
        debt['discipline_name'] = disc.get('name', '—')
        debt['discipline_code'] = disc.get('code', '')
        debt['department'] = disc.get('department', '')
        debt['student_name'] = student.get('full_name', '—')
        debt['student_email'] = student.get('email', '—')
        debt['group_name'] = group_map.get(student.get('group_id'), '—')
        debt['teacher_name'] = teacher.get('full_name', '—')
        debt['teacher_department'] = teacher.get('department', '')
        debt['control_type_display'] = CONTROL_TYPES.get(debt.get('control_type', ''), debt.get('control_type', '—'))
        debt['debt_type_display'] = DEBT_TYPES.get(debt.get('debt_type', ''), debt.get('debt_type', '—'))
        debt['status_display'] = STATUS_MAP.get(debt.get('status', ''), debt.get('status', '—'))
        debt['semester_display'] = f"{debt.get('semester', '?')} семестр"

    return all_debts


def apply_filters(debts, search='', group='', status='', control=''):
    """Фильтрует долги"""
    filtered = []
    for d in debts:
        if search:
            search_lower = search.lower()
            if (search_lower not in d.get('student_name', '').lower() and
                search_lower not in d.get('student_email', '').lower() and
                search_lower not in d.get('group_name', '').lower() and
                search_lower not in d.get('discipline_name', '').lower()):
                continue
        
        if group and d.get('group_name', '') != group:
            continue
        
        if status and d.get('status', '') != status:
            continue
        
        if control and d.get('control_type', '') != control:
            continue
        
        filtered.append(d)
    
    return filtered


def group_by_discipline(debts):
    """Группирует долги по дисциплинам"""
    grouped = OrderedDict()
    for d in debts:
        disc_id = d.get('discipline_id')
        if disc_id not in grouped:
            grouped[disc_id] = {
                'discipline_name': d.get('discipline_name', '—'),
                'discipline_code': d.get('discipline_code', ''),
                'department': d.get('department', ''),
                'teacher_name': d.get('teacher_name', '—'),
                'debts': [],
                'total_count': 0,
                'open_count': 0,
                'passed_count': 0,
                'failed_count': 0,
            }
        
        grouped[disc_id]['debts'].append(d)
        grouped[disc_id]['total_count'] += 1
        
        st = d.get('status', '')
        if st in ['open', 'in_progress']:
            grouped[disc_id]['open_count'] += 1
        elif st == 'passed':
            grouped[disc_id]['passed_count'] += 1
        elif st == 'failed':
            grouped[disc_id]['failed_count'] += 1
    
    return grouped


@login_required
@user_passes_test(is_dean)
def debts_summary(request):
    api = EmulatorAPI()
    
    search = request.GET.get('search', '').strip()
    group = request.GET.get('group', '').strip()
    status = request.GET.get('status', '').strip()
    control = request.GET.get('control', '').strip()
    
    try:
        all_debts, disciplines, teachers, groups, accounts = get_all_data(api)
        enriched = enrich_debts(all_debts, disciplines, teachers, groups, accounts)
        filtered = apply_filters(enriched, search, group, status, control)
        grouped = group_by_discipline(filtered)
    except Exception as e:
        print(f"Error: {e}")
        return render(request, 'reports/debts_summary.html', {
            'grouped_summary': {},
            'total_debts': 0,
            'groups': [],
            'control_types': [],
            'error': str(e)
        })

    # Собираем все возможные значения для фильтров
    all_enriched = enrich_debts(all_debts, disciplines, teachers, groups, accounts)
    all_groups = sorted({d.get('group_name') for d in all_enriched if d.get('group_name') != '—'})
    all_controls = sorted({d.get('control_type') for d in all_enriched if d.get('control_type')})

    # Сохраняем параметры в сессию для экспорта
    request.session['report_filters'] = {
        'search': search,
        'group': group,
        'status': status,
        'control': control,
    }

    return render(request, 'reports/debts_summary.html', {
        'grouped_summary': grouped,
        'total_debts': len(filtered),
        'groups': all_groups,
        'control_types': all_controls,
        'current_filters': {
            'search': search,
            'group': group,
            'status': status,
            'control': control,
        }
    })


@login_required
@user_passes_test(is_dean)
def export_debts_excel(request):
    api = EmulatorAPI()
    filters = request.session.get('report_filters', {})
    
    all_debts, disciplines, teachers, groups, accounts = get_all_data(api)
    enriched = enrich_debts(all_debts, disciplines, teachers, groups, accounts)
    filtered = apply_filters(
        enriched,
        filters.get('search', ''),
        filters.get('group', ''),
        filters.get('status', ''),
        filters.get('control', '')
    )
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow([
        'Дисциплина', 'Студент', 'Email', 'Группа', 'Преподаватель',
        'Тип контроля', 'Причина', 'Семестр', 'Статус', 'Оценка'
    ])
    
    for d in filtered:
        writer.writerow([
            d.get('discipline_name', '—'),
            d.get('student_name', '—'),
            d.get('student_email', '—'),
            d.get('group_name', '—'),
            d.get('teacher_name', '—'),
            d.get('control_type_display', '—'),
            d.get('debt_type_display', '—'),
            d.get('semester_display', '—'),
            d.get('status_display', '—'),
            d.get('grade', '—'),
        ])
    
    response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="debts_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    return response


@login_required
@user_passes_test(is_dean)
def export_debts_word(request):
    api = EmulatorAPI()
    filters = request.session.get('report_filters', {})
    
    all_debts, disciplines, teachers, groups, accounts = get_all_data(api)
    enriched = enrich_debts(all_debts, disciplines, teachers, groups, accounts)
    filtered = apply_filters(
        enriched,
        filters.get('search', ''),
        filters.get('group', ''),
        filters.get('status', ''),
        filters.get('control', '')
    )
    
    total = len(filtered)
    open_count = sum(1 for d in filtered if d.get('status') in ['open', 'in_progress'])
    passed_count = sum(1 for d in filtered if d.get('status') == 'passed')
    failed_count = sum(1 for d in filtered if d.get('status') == 'failed')
    
    # Группируем по студентам
    students = OrderedDict()
    for d in filtered:
        name = d.get('student_name', '—')
        if name not in students:
            students[name] = {
                'group': d.get('group_name', '—'),
                'debts': [],
                'open': 0,
                'passed': 0,
                'failed': 0,
            }
        students[name]['debts'].append(d)
        st = d.get('status', '')
        if st in ['open', 'in_progress']:
            students[name]['open'] += 1
        elif st == 'passed':
            students[name]['passed'] += 1
        elif st == 'failed':
            students[name]['failed'] += 1
    
    # Группируем по дисциплинам
    grouped = group_by_discipline(filtered)
    
    filters_text = ''
    if filters.get('group'):
        filters_text += f' по группе {filters["group"]}'
    if filters.get('status'):
        status_names = {'open': 'открытые', 'passed': 'сданные', 'failed': 'просроченные'}
        filters_text += f' ({status_names.get(filters["status"], filters["status"])})'
    
    html = f'''
    <html xmlns:o="urn:schemas-microsoft-com:office:office"
          xmlns:w="urn:schemas-microsoft-com:office:word"
          xmlns="http://www.w3.org/TR/REC-html40">
    <head>
        <meta charset="utf-8">
        <title>Отчёт по задолженностям</title>
        <style>
            body {{ font-family: 'Times New Roman', serif; font-size: 14pt; line-height: 1.5; padding: 40px; }}
            h1 {{ text-align: center; font-size: 18pt; margin-bottom: 30px; }}
            h2 {{ font-size: 16pt; margin-top: 25px; }}
            h3 {{ font-size: 14pt; margin-top: 20px; }}
            p {{ margin: 10px 0; text-indent: 30px; }}
            .bad {{ color: #c0392b; font-weight: bold; }}
            .good {{ color: #27ae60; font-weight: bold; }}
            .warn {{ color: #f39c12; font-weight: bold; }}
            .date {{ text-align: right; color: #7f8c8d; margin-bottom: 30px; }}
        </style>
    </head>
    <body>
        <h1>Аналитический отчёт по академическим задолженностям</h1>
        <p class="date">Дата: {datetime.now().strftime("%d.%m.%Y %H:%M")}</p>
        
        <h2>1. Общая сводка</h2>
        <p>Всего задолженностей{filters_text}: <span class="bad">{total}</span>.</p>
        <p>Из них:</p>
        <p>- Открытых (в процессе): <span class="warn">{open_count}</span>.</p>
        <p>- Успешно закрытых: <span class="good">{passed_count}</span>.</p>
        <p>- Просроченных: <span class="bad">{failed_count}</span>.</p>
        
        <h2>2. Студенты с задолженностями</h2>
        <p>Всего студентов: {len(students)}.</p>
    '''
    
    if students:
        html += '<p>Список студентов:</p>'
        for name, info in students.items():
            debts_desc = []
            for d in info['debts']:
                debts_desc.append(f"{d.get('discipline_name', '')} ({d.get('control_type_display', '').lower()})")
            debts_text = '; '.join(debts_desc)
            status_text = f"открыто: {info['open']}, сдано: {info['passed']}, просрочено: {info['failed']}"
            html += f'<p>- {name}, группа {info["group"]}. Задолженности: {debts_text}. Статистика: {status_text}.</p>'
    
    html += '''
        <h2>3. Анализ по дисциплинам</h2>
    '''
    
    for disc_id, data in grouped.items():
        html += f'''
            <h3>{data['discipline_name']}</h3>
            <p>Преподаватель: {data['teacher_name']}. Кафедра: {data['department']}.</p>
            <p>Всего задолженностей: {data['total_count']} (открыто: {data['open_count']}, сдано: {data['passed_count']}, просрочено: {data['failed_count']}).</p>
        '''
        
        disc_students = {}
        for d in data['debts']:
            name = d.get('student_name', '—')
            if name not in disc_students:
                disc_students[name] = []
            disc_students[name].append(d)
        
        if disc_students:
            html += '<p>Студенты:</p>'
            for name, debts in disc_students.items():
                reasons = ', '.join([f"{d.get('control_type_display', '')} - {d.get('debt_type_display', '')}" for d in debts])
                html += f'<p>- {name}: {reasons}.</p>'
    
    html += '''
        <h2>4. Рекомендации</h2>
    '''
    
    if failed_count > 0:
        html += f'<p>Выявлено <span class="bad">{failed_count}</span> просроченных задолженностей. Рекомендуется назначить пересдачи.</p>'
    
    if total > 0:
        if passed_count / total > 0.5:
            html += f'<p class="good">Более половины задолженностей успешно закрыты. Положительная динамика.</p>'
        if open_count / total > 0.5:
            html += f'<p class="warn">Более половины задолженностей остаются открытыми. Требуется усиление контроля.</p>'
    
    if total == 0:
        html += '<p>Задолженностей по заданным критериям не найдено.</p>'
    
    html += '''
        <br><br>
        <p>Отчёт подготовлен системой «АкадемКонтроль».</p>
    </body>
    </html>
    '''
    
    response = HttpResponse(html, content_type='application/msword; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.doc"'
    return response