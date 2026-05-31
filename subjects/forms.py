from django import forms
from .models import Subject, Enrollment
from django.contrib.auth.models import User
from accounts.models import Profile

class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'description', 'teachers', 'groups']
        widgets = {
            'teachers': forms.CheckboxSelectMultiple(),
            'groups': forms.CheckboxSelectMultiple(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        teachers = User.objects.filter(
            profile__role='teacher'
        ).select_related('profile').order_by('last_name', 'first_name')
        
        teacher_choices = []
        for teacher in teachers:
            profile = teacher.profile
            full_name = f"{teacher.last_name} {teacher.first_name}"
            if profile.patronymic:
                full_name += f" {profile.patronymic}"
            
            label = f"{full_name} ({teacher.email})"
            teacher_choices.append((teacher.id, label))
        
        self.fields['teachers'].choices = teacher_choices
        self.fields['teachers'].label = 'Выберите преподавателей'
        
        for field_name, field in self.fields.items():
            if field_name == 'teachers':
                field.widget.attrs.update({'class': 'teacher-checkboxes'})
            elif field_name == 'groups':
                field.widget.attrs.update({'class': 'group-checkboxes'})
                field.label = 'Выберите группы'
            else:
                field.widget.attrs.update({
                    'class': 'form-control rounded-pill',
                    'placeholder': field.label
                })
        
        self.fields['description'].widget.attrs.update({
            'placeholder': 'Краткое описание предмета...',
            'rows': 3,
            'class': 'form-control rounded-4'
        })

class GradeForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ['grade', 'status']
        widgets = {
            'status': forms.Select(
                choices=Enrollment.Status.choices,
                attrs={'class': 'form-select'}
            ),
            'grade': forms.TextInput(
                attrs={
                    'class': 'form-control rounded-pill',
                    'placeholder': '5, 4, Зачёт...'
                }
            )
        }