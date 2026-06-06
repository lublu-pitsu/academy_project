from django.db import models
import uuid
from datetime import timedelta

class Retake(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discipline_name = models.CharField(max_length=300)
    type = models.CharField(max_length=20)  # regular или commission
    building_number = models.CharField(max_length=10)
    classroom_number = models.CharField(max_length=10)
    start_at = models.DateTimeField()
    duration_minutes = models.IntegerField()
    status = models.CharField(max_length=20)  
    students = models.JSONField(default=list) 
    teachers = models.JSONField(default=list)  
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def end_time(self):
        if self.start_at and self.duration_minutes:
            return self.start_at + timedelta(minutes=self.duration_minutes)
        return None

    class Meta:
        ordering = ['-start_at']

    def __str__(self):
        return f"{self.discipline_name} ({self.start_at.strftime('%d.%m.%Y %H:%M')})"