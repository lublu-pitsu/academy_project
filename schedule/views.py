from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date
from datetime import date, timedelta
from retakes.models import Retake
from collections import defaultdict

RUS_WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

@login_required
def schedule_view(request):
    date_str = request.GET.get('date', '')
    if date_str:
        base_date = parse_date(date_str) or date.today()
    else:
        base_date = date.today()

    monday = base_date - timedelta(days=base_date.weekday())
    sunday = monday + timedelta(days=6)

    week_retakes = Retake.objects.filter(
        start_at__date__gte=monday,
        start_at__date__lte=sunday
    ).order_by('start_at')

    retakes_by_day = defaultdict(list)
    for r in week_retakes:
        day_key = r.start_at.date()
        retakes_by_day[day_key].append(r)

    days = []
    for i in range(7):
        current_date = monday + timedelta(days=i)
        day_info = {
            'date': current_date,
            'weekday': RUS_WEEKDAYS[i],
            'is_today': current_date == date.today(),
            'has_retakes': current_date in retakes_by_day,
            'retakes': retakes_by_day.get(current_date, []),
        }
        days.append(day_info)

    prev_week = monday - timedelta(days=7)
    next_week = monday + timedelta(days=7)

    context = {
        'days': days,
        'monday': monday,
        'sunday': sunday,
        'prev_week': prev_week,
        'next_week': next_week,
        'selected_date': base_date,                
        'current_week_label': f'{monday.strftime("%d.%m")} – {sunday.strftime("%d.%m")}',
    }
    return render(request, 'schedule/calendar.html', context)