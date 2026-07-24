from django.db import models
from django.contrib.auth.models import User

class UserSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_id = models.CharField(max_length=100, unique=True)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    device_info = models.TextField(blank=True)

    def __str__(self):
        return f"Session {self.session_id} - {self.user}"

class VitalSignLog(models.Model):
    session = models.ForeignKey(UserSession, on_delete=models.CASCADE, related_name='logs')
    timestamp = models.DateTimeField(auto_now_add=True)
    bpm = models.FloatField()
    rr = models.FloatField()
    signal_quality = models.IntegerField()

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} | BPM: {self.bpm} | RR: {self.rr}"
