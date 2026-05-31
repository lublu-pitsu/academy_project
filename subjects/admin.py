from django.contrib import admin
from .models import Subject, StudentGroup, Enrollment

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    filter_horizontal = ('teachers', 'groups')
    list_display = ('name',)

@admin.register(StudentGroup)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('number',)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'grade', 'status')
    list_filter = ('subject', 'status')