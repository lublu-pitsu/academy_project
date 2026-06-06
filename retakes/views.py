from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from api_client import EmulatorAPI
from datetime import datetime
import csv
import io
import json
from .models import Retake

def is_dean(user):
    return hasattr(user, 'profile') and user.profile.role == 'dean'

def is_teacher(user):
    return hasattr(user, 'profile') and user.profile.role == 'teacher'

def is_student(user):
    return hasattr(user, 'profile') and user.profile.role == 'student'


@login_required
@user_passes_test(is_dean)
def retake_summary(request):
    retakes = Retake.objects.all()
    return render(request, 'retakes/retake_summary.html', {'retakes': retakes})


@login_required
@user_passes_test(is_dean)
def create_retake(request):
    if request.method == 'POST':
        access_token = request.session.get('access_token')
        if not access_token:
            return render(request, 'retakes/create_retake.html', {'error': 'Нет доступа'})

        api = EmulatorAPI()
        discipline_id = request.POST.get('discipline_id')
        teacher_ids = request.POST.getlist('teachers')
        retake_type = request.POST.get('type', 'regular')
        building = request.POST.get('building_number')
        classroom = request.POST.get('classroom_number')
        start_at = request.POST.get('start_at')
        duration = request.POST.get('duration_minutes', 90)

        if retake_type == 'commission' and len(teacher_ids) < 3:
            return render(request, 'retakes/create_retake.html', {
                'error': 'Для комиссии необходимо минимум 3 преподавателя',
                'form_data': request.POST
            })

        try:
            debts = api.get_debts_for_discipline(discipline_id)
            student_ids = list(set(d.get('student_id') for d in debts if d.get('student_id')))
        except Exception as e:
            return render(request, 'retakes/create_retake.html', {
                'error': f'Не удалось загрузить студентов: {e}',
                'form_data': request.POST
            })

        if not student_ids:
            return render(request, 'retakes/create_retake.html', {
                'error': 'Нет студентов с открытыми долгами по этой дисциплине',
                'form_data': request.POST
            })

        payload = {
            'discipline_id': discipline_id,
            'students': student_ids,
            'teachers': teacher_ids,
            'type': retake_type,
            'building_number': building,
            'classroom_number': classroom,
            'start_at': start_at,
            'duration_minutes': int(duration)
        }
        try:
            result = api.create_dean_retake(payload, access_token)

            teachers = api.get_teachers()
            teacher_dict = {}
            for t in teachers:
                tid = t.get('id')
                if tid:
                    teacher_dict[tid] = t.get('full_name') or f"{t.get('last_name','')} {t.get('first_name','')} {t.get('middle_name','')}".strip()
            teacher_names = [teacher_dict.get(tid, tid) for tid in teacher_ids]

            students = api.get_students()
            student_dict = {}
            for s in students:
                sid = s.get('id')
                if sid:
                    student_dict[sid] = f"{s.get('last_name','')} {s.get('first_name','')} {s.get('middle_name','')}".strip()
            student_names = [student_dict.get(sid, sid) for sid in student_ids]

            Retake.objects.create(
                id=result['id'],
                discipline_name=result.get('discipline_name', ''),
                type=result['type'],
                building_number=result['building_number'],
                classroom_number=result['classroom_number'],
                start_at=result['start_at'],
                duration_minutes=result['duration_minutes'],
                status=result['status'],
                students=student_names,
                teachers=teacher_names,
            )
            return redirect('retake_summary')
        except Exception as e:
            return render(request, 'retakes/create_retake.html', {
                'error': f'Ошибка создания пересдачи: {e}',
                'form_data': request.POST
            })

    api = EmulatorAPI()
    try:
        disciplines = api.get_disciplines()
    except Exception:
        disciplines = []
    return render(request, 'retakes/create_retake.html', {'disciplines': disciplines})


@login_required
@user_passes_test(is_dean)
def sync_retakes(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return HttpResponse('Нет доступа', status=403)

    api = EmulatorAPI()
    try:
        csv_content = api.export_retakes_csv(access_token)
        reader = csv.DictReader(io.StringIO(csv_content))
        for row in reader:
            retake_id = row.get('retake_id')
            if not retake_id:
                continue
            students_raw = row.get('students', '')
            student_names = [s.strip() for s in students_raw.split(',') if s.strip()] if students_raw else []
            teachers_raw = row.get('teachers', '')
            teacher_names = [t.strip() for t in teachers_raw.split(',') if t.strip()] if teachers_raw else []
            Retake.objects.update_or_create(
                id=retake_id,
                defaults={
                    'discipline_name': row.get('discipline', ''),
                    'type': row.get('type', 'regular'),
                    'building_number': row.get('building', ''),
                    'classroom_number': row.get('classroom', ''),
                    'start_at': row.get('date'),
                    'duration_minutes': int(row.get('duration_minutes', 90)),
                    'status': row.get('status', 'scheduled'),
                    'students': student_names,
                    'teachers': teacher_names,
                }
            )
        return redirect('retake_summary')
    except Exception as e:
        return HttpResponse(f'Ошибка синхронизации: {e}', status=500)


@login_required
@user_passes_test(is_dean)
def retake_requests_list(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return render(request, 'retakes/retake_requests.html', {'requests': [], 'error': 'Нет доступа'})
    api = EmulatorAPI()
    retake_requests = []
    try:
        data = api.get_dean_retake_requests(access_token)
        print(f"[DEBUG] Заявки: {json.dumps(data, indent=2, ensure_ascii=False)}")
        retake_requests = data if isinstance(data, list) else data.get('data', [])
        
        retake_requests = [r for r in retake_requests if r.get('status') in ('pending', 'open')]
        
        retake_map = {str(r.id): r.discipline_name for r in Retake.objects.all()}
        disciplines = {}
        try:
            disc_list = api.get_disciplines()
            disciplines = {d['id']: d.get('name', '') for d in disc_list}
        except:
            pass
        
        teacher_map = {}
        try:
            teachers = api.get_teachers()
            for t in teachers:
                teacher_map[t['id']] = f"{t.get('last_name', '')} {t.get('first_name', '')} {t.get('middle_name', '')}".strip()
        except:
            pass
        
        for req in retake_requests:
            if req.get('kind') == 'modify' and req.get('retake_id'):
                req['discipline_name'] = retake_map.get(req['retake_id'], 'Дисциплина не найдена')
            elif req.get('kind') == 'create' and req.get('discipline_id'):
                req['discipline_name'] = disciplines.get(req['discipline_id'], 'Дисциплина не указана')
            else:
                req['discipline_name'] = 'Дисциплина не указана'
            req['teacher_name'] = teacher_map.get(req.get('teacher_id'), 'Не указан')
    except Exception as e:
        print(f"[DEBUG] Ошибка загрузки заявок: {e}")
    return render(request, 'retakes/retake_requests.html', {'requests': retake_requests})


@login_required
@user_passes_test(is_dean)
def review_retake_request(request, request_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'error': 'Метод не поддерживается'}, status=400)

    access_token = request.session.get('access_token')
    if not access_token:
        return JsonResponse({'status': 'error', 'error': 'Нет доступа'}, status=403)

    decision = request.POST.get('decision')
    comment = request.POST.get('review_comment', '')
    retake_id = request.POST.get('retake_id')
    start_at = request.POST.get('start_at')
    building = request.POST.get('building_number')
    classroom = request.POST.get('classroom_number')

    api = EmulatorAPI()
    try:
        result = api.review_retake_request(request_id, decision, comment, access_token)
        print(f"[DEBUG] Review API response: {result}")
        
        if decision == 'approved':
            kind = result.get('kind')
            if kind == 'create':
                discipline_id = result.get('discipline_id')
                teacher_id = result.get('teacher_id')
                
                teacher_name = teacher_id
                try:
                    teachers = api.get_teachers()
                    for t in teachers:
                        if t['id'] == teacher_id:
                            teacher_name = f"{t.get('last_name', '')} {t.get('first_name', '')} {t.get('middle_name', '')}".strip()
                            if not teacher_name:
                                teacher_name = t.get('email', teacher_id)
                            break
                except Exception as e:
                    print(f"[WARN] Не удалось получить имя преподавателя: {e}")
                try:
                    debts = api.get_debts_for_discipline(discipline_id)
                    student_ids = list(set(d.get('student_id') for d in debts if d.get('student_id')))
                except Exception as e:
                    print(f"[WARN] Не удалось получить студентов: {e}")
                    student_ids = []
                
                student_names = []
                try:
                    students = api.get_students()
                    student_dict = {s['id']: f"{s.get('last_name', '')} {s.get('first_name', '')} {s.get('middle_name', '')}".strip() for s in students}
                    student_names = [student_dict.get(sid, sid) for sid in student_ids]
                except Exception as e:
                    print(f"[WARN] Не удалось получить имена студентов: {e}")
                    student_names = [str(sid) for sid in student_ids]
                
                disc_name = ''
                try:
                    disc_list = api.get_disciplines()
                    for d in disc_list:
                        if d['id'] == discipline_id:
                            disc_name = d.get('name', '')
                            break
                except:
                    disc_name = 'Дисциплина'
                
                payload = {
                    'discipline_id': discipline_id,
                    'students': student_ids,
                    'teachers': [teacher_id],
                    'type': 'regular',
                    'building_number': result.get('proposed_building_number', building or ''),
                    'classroom_number': result.get('proposed_classroom_number', classroom or ''),
                    'start_at': result.get('proposed_start_at', start_at),
                    'duration_minutes': 90,
                }
                try:
                    create_result = api.create_dean_retake(payload, access_token)
                    print(f"[DEBUG] Created retake: {create_result}")
                    new_retake_id = create_result.get('id')
                    if new_retake_id:
                        Retake.objects.update_or_create(
                            id=new_retake_id,
                            defaults={
                                'discipline_name': disc_name,
                                'type': 'regular',
                                'building_number': payload['building_number'],
                                'classroom_number': payload['classroom_number'],
                                'start_at': payload['start_at'],
                                'duration_minutes': payload['duration_minutes'],
                                'status': 'scheduled',
                                'students': student_names,
                                'teachers': [teacher_name],
                            }
                        )
                except Exception as e:
                    print(f"[ERROR] Failed to create retake: {e}")

            elif kind == 'modify' and retake_id:
                try:
                    retake = Retake.objects.get(id=retake_id)
                    if start_at:
                        retake.start_at = start_at
                    if building:
                        retake.building_number = building
                    if classroom:
                        retake.classroom_number = classroom
                    retake.save()
                    print(f"[DEBUG] Обновлена пересдача: {retake_id}")
                except Retake.DoesNotExist:
                    print(f"[WARN] Пересдача {retake_id} не найдена в БД")
        return JsonResponse({'status': 'ok'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'status': 'error', 'error': str(e)}, status=400)


@login_required
@user_passes_test(is_dean)
def export_retakes_csv(request):
    access_token = request.session.get('access_token')
    if not access_token:
        return HttpResponse('Нет доступа', status=403)
    api = EmulatorAPI()
    try:
        csv_content = api.export_retakes_csv(access_token)
        response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="retakes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        return response
    except Exception as e:
        return HttpResponse(f'Ошибка экспорта: {e}', status=500)


@login_required
@user_passes_test(is_teacher)
def teacher_retakes(request):
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    if not access_token:
        return render(request, 'retakes/teacher_retakes.html', {'retakes': [], 'error': 'Нет доступа'})
    api = EmulatorAPI()
    retakes = []
    try:
        items, new_access, new_refresh = api.get_teacher_retakes(access_token, refresh_token)
        active_statuses = ['scheduled', 'in_progress']
        retakes = [r for r in items if r.get('status') in active_statuses]
        if new_access and new_access != access_token:
            request.session['access_token'] = new_access
            request.session['refresh_token'] = new_refresh
    except Exception:
        pass
    return render(request, 'retakes/teacher_retakes.html', {'retakes': retakes})


@login_required
@user_passes_test(is_teacher)
def create_retake_request(request):
    if request.method == 'POST':
        access_token = request.session.get('access_token')
        refresh_token = request.session.get('refresh_token')
        if not access_token:
            return render(request, 'retakes/create_retake_request.html', {'error': 'Нет доступа'})
        api = EmulatorAPI()
        kind = request.POST.get('kind', 'modify')
        
        proposed_options_raw = request.POST.get('proposed_options', '').strip()
        if proposed_options_raw:
            try:
                proposed_options = json.loads(proposed_options_raw)
            except json.JSONDecodeError:
                proposed_options = {}
        else:
            proposed_options = {}
        
        def to_iso(dt_str):
            if not dt_str:
                return None
            if len(dt_str) == 16:  
                dt_str += ':00'
            if not dt_str.endswith('Z') and '+' not in dt_str and len(dt_str) <= 19:
                dt_str += '+00:00'
            return dt_str
        
        payload = {
            'kind': kind,
            'teacher_id': request.POST.get('teacher_id'),
            'proposed_start_at': to_iso(request.POST.get('proposed_start_at')),
            'proposed_end_at': to_iso(request.POST.get('proposed_end_at')),
            'proposed_building_number': request.POST.get('proposed_building_number'),
            'proposed_classroom_number': request.POST.get('proposed_classroom_number'),
            'proposed_options': proposed_options,
            'comment': request.POST.get('comment', ''),
        }
        if kind == 'modify':
            payload['retake_id'] = request.POST.get('retake_id')
        else:
            payload['discipline_id'] = request.POST.get('discipline_id')
            
        try:
            result, new_access, new_refresh = api.create_teacher_retake_request(payload, access_token, refresh_token)
            if new_access and new_access != access_token:
                request.session['access_token'] = new_access
                request.session['refresh_token'] = new_refresh
            return redirect('teacher_retakes')
        except Exception as e:
            return render(request, 'retakes/create_retake_request.html', {
                'error': str(e),
                'form_data': request.POST
            })
    
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    if not access_token:
        return render(request, 'retakes/create_retake_request.html', {'error': 'Нет доступа'})

    api = EmulatorAPI()
    teacher_retakes = []
    teacher_disciplines = []
    teacher_id = None
    try:
        me = api.get_app_me(access_token)
        teacher_id = me.get('linked_entity_id')
        
        all_debts = api.get_debts()
        teacher_debts = [d for d in all_debts if d.get('teacher_id') == teacher_id]
        disc_ids = {d.get('discipline_id') for d in teacher_debts if d.get('discipline_id')}
        
        all_disciplines = api.get_disciplines()
        teacher_disciplines = [d for d in all_disciplines if d['id'] in disc_ids]
        
        items, new_access, new_refresh = api.get_teacher_retakes(access_token, refresh_token)
        active_statuses = ['scheduled', 'in_progress']
        teacher_retakes = [r for r in items if r.get('status') in active_statuses]
        if new_access and new_access != access_token:
            request.session['access_token'] = new_access
            request.session['refresh_token'] = new_refresh
    except Exception as e:
        print(f"Error loading teacher data: {e}")
        teacher_disciplines = []
        teacher_retakes = []

    return render(request, 'retakes/create_retake_request.html', {
        'disciplines': teacher_disciplines,
        'retakes': teacher_retakes,
        'teacher_id': teacher_id,
    })


@login_required
@user_passes_test(is_student)
def student_retakes(request):
    access_token = request.session.get('access_token')
    refresh_token = request.session.get('refresh_token')
    if not access_token:
        return render(request, 'retakes/student_retakes.html', {'retakes': [], 'error': 'Нет доступа'})
    api = EmulatorAPI()
    retakes = []
    try:
        items, new_access, new_refresh = api.get_student_retakes(access_token, refresh_token)
        retakes = items
        if new_access and new_access != access_token:
            request.session['access_token'] = new_access
            request.session['refresh_token'] = new_refresh
    except Exception:
        pass
    return render(request, 'retakes/student_retakes.html', {'retakes': retakes})


@login_required
@user_passes_test(is_dean)
def students_with_debts(request):
    discipline_id = request.GET.get('discipline_id')
    if not discipline_id:
        return JsonResponse({'error': 'discipline_id required'}, status=400)
    api = EmulatorAPI()
    try:
        debts = api.get_debts_for_discipline(discipline_id)
        student_ids = list(set(d.get('student_id') for d in debts if d.get('student_id')))
        return JsonResponse({'student_ids': student_ids})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)