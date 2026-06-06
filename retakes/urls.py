from django.urls import path
from . import views

urlpatterns = [
    path('', views.retake_summary, name='retake_summary'),
    path('create/', views.create_retake, name='create_retake'),
    path('sync/', views.sync_retakes, name='sync_retakes'),
    path('requests/', views.retake_requests_list, name='retake_requests_list'),
    path('requests/<uuid:request_id>/review/', views.review_retake_request, name='review_retake_request'),
    path('export/csv/', views.export_retakes_csv, name='export_retakes_csv'),
    path('teacher/', views.teacher_retakes, name='teacher_retakes'),
    path('teacher/request/', views.create_retake_request, name='create_retake_request'),
    path('my/', views.student_retakes, name='student_retakes'),
    path('students-with-debts/', views.students_with_debts, name='students_with_debts'),
]