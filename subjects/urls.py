from django.urls import path
from . import views

urlpatterns = [
    path('', views.subject_list, name='subject_list'),
    path('teacher/', views.teacher_subjects, name='teacher_subjects'),
    path('teacher/<uuid:subject_pk>/', views.subject_students, name='subject_students'),
    path('grade/<uuid:enrollment_pk>/', views.update_grade, name='update_grade'),
    path('my/', views.my_subjects, name='my_subjects'),
    path('groups/', views.group_list, name='group_list'),
]