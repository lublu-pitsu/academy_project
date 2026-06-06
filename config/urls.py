from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('subjects/', include('subjects.urls')),
    path('reports/', include('reports.urls')),
    path('retakes/', include('retakes.urls')),
    path('schedule/', include('schedule.urls')),
]