from django.urls import path
from . import views

urlpatterns = [
    path('', views.debts_summary, name='debts_summary'),
    path('export/excel/', views.export_debts_excel, name='export_debts_excel'),
    path('export/word/', views.export_debts_word, name='export_debts_word'),
]