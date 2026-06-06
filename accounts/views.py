from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from api_client import EmulatorAPI
from .models import Profile

def is_dean(user):
    try:
        return user.profile.role == 'dean'
    except Profile.DoesNotExist:
        return False

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('menu')
        else:
            return render(request, 'accounts/login.html', {
                'error': 'Неверный email или пароль'
            })
    return render(request, 'accounts/login.html')

@login_required
def profile(request):
    profile = request.user.profile
    return render(request, 'accounts/profile.html', {'profile': profile})

@login_required
@user_passes_test(is_dean)
def student_list(request):
    api = EmulatorAPI()
    try:
        students = api.get_students()
        groups = api.get_groups()
        accounts = api.get_accounts(role='student')
    except Exception as e:
        print(f"Error loading data: {e}")
        students, groups, accounts = [], [], []

    email_map = {}
    for acc in accounts:
        if acc.get('linked_entity_type') == 'student' and acc.get('linked_entity_id'):
            email_map[acc['linked_entity_id']] = acc.get('email', '-')

    group_dict = {}
    for g in groups:
        group_dict[g['id']] = {
            'name': g.get('name', '-'),
            'course': g.get('course', '-')
        }

    for s in students:
        s['email'] = email_map.get(s.get('id'), '-')
        gid = s.get('group_id')
        info = group_dict.get(gid, {})
        s['group_name'] = info.get('name', '-')
        s['course'] = info.get('course', '-')

    courses = sorted({s['course'] for s in students if s['course'] != '-'}, key=str)
    group_names = sorted({s['group_name'] for s in students if s['group_name'] != '-'})

    return render(request, 'accounts/student_list.html', {
        'students': students,
        'courses': courses,
        'groups': group_names,
    })

@login_required
@user_passes_test(is_dean)
def filter_students(request):
    search = request.GET.get('search', '').strip().lower()
    course = request.GET.get('course', '')
    group = request.GET.get('group', '')

    api = EmulatorAPI()
    try:
        students = api.get_students()
        groups = api.get_groups()
        accounts = api.get_accounts(role='student')
    except Exception as e:
        return JsonResponse({'students': [], 'error': str(e)})

    email_map = {}
    for acc in accounts:
        if acc.get('linked_entity_type') == 'student' and acc.get('linked_entity_id'):
            email_map[acc['linked_entity_id']] = acc.get('email', '-')

    group_dict = {}
    for g in groups:
        group_dict[g['id']] = {
            'name': g.get('name', '-'),
            'course': g.get('course', '-')
        }

    filtered = []
    for s in students:
        s_email = email_map.get(s.get('id'), '-')
        gid = s.get('group_id')
        info = group_dict.get(gid, {})
        s_group = info.get('name', '-')
        s_course = info.get('course', '-')

        full_name = f"{s.get('last_name','')} {s.get('first_name','')} {s.get('middle_name','')}".strip()

        if search:
            if (search not in full_name.lower() and
                search not in s_email.lower() and
                search not in s_group.lower()):
                continue
        if course and str(s_course) != course:
            continue
        if group and s_group != group:
            continue

        filtered.append({
            'id': s.get('id'),
            'full_name': full_name,
            'email': s_email,
            'course': s_course,
            'group_number': s_group,
        })

    return JsonResponse({'students': filtered})