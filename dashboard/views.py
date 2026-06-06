from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import Profile

def home(request):
    return render(request, 'dashboard/home.html')

@login_required
def menu(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        Profile.objects.create(user=request.user)
        profile = request.user.profile
    
    functions = [
        {
            'name': 'Личный кабинет',
            'url': 'profile',
            'icon': 'fa-id-card',
            'description': 'Ваши личные данные',
        }
    ]
    
    if profile.role == 'dean':
        functions.append({
            'name': 'Список студентов',
            'url': 'student_list',
            'icon': 'fa-users',
            'description': 'Просмотр и редактирование студентов',
        })
        functions.append({
            'name': 'Список предметов',
            'url': 'subject_list',
            'icon': 'fa-book',
            'description': 'Создание и управление предметами',
        })
        functions.append({
            'name': 'Список групп',
            'url': 'group_list',
            'icon': 'fa-layer-group',
            'description': 'Создание и управление группами',
        })
        functions.append({
            'name': 'Сводка по задолженностям',
            'url': 'debts_summary',
            'icon': 'fa-chart-bar',
            'description': 'Просмотр и экспорт отчётов',
        })
        functions.append({
            'name': 'Управление пересдачами',
            'url': 'retake_summary',
            'icon': 'fa-clock-rotate-left',
            'description': 'Создание и просмотр пересдач',
        })
        functions.append({
            'name': 'Заявки на пересдачи',
            'url': 'retake_requests_list',
            'icon': 'fa-envelope-open-text',
            'description': 'Обработка заявок преподавателей',
        })
        functions.append({
            'name': 'Расписание пересдач',
            'url': 'schedule',
            'icon': 'fa-calendar-alt',
            'description': 'Календарь всех пересдач',
        })
        
    elif profile.role == 'teacher':
        functions.append({
            'name': 'Мои предметы',
            'url': 'teacher_subjects',
            'icon': 'fa-book-open',
            'description': 'Управление задолженностями студентов',
        })
        functions.append({
            'name': 'Мои пересдачи',
            'url': 'teacher_retakes',
            'icon': 'fa-calendar-check',
            'description': 'Просмотр и заявки по пересдачам',
        })
        functions.append({
            'name': 'Расписание пересдач',
            'url': 'schedule',
            'icon': 'fa-calendar-alt',
            'description': 'Календарь всех пересдач',
        })
    elif profile.role == 'student':
        functions.append({
            'name': 'Мои предметы',
            'url': 'my_subjects',
            'icon': 'fa-book-open-reader',
            'description': 'Моя успеваемость и задолженности',
        })
        functions.append({
            'name': 'Мои пересдачи',
            'url': 'student_retakes',
            'icon': 'fa-calendar-day',
            'description': 'Расписание моих пересдач',
        })
        functions.append({
            'name': 'Расписание пересдач',
            'url': 'schedule',
            'icon': 'fa-calendar-alt',
            'description': 'Календарь всех пересдач',
        })
    
    return render(request, 'dashboard/menu.html', {'functions': functions})