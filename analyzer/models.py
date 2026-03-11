from django.db import models
from django.contrib.auth.models import User

class UploadedReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='reports/')
    
    def __str__(self):
        return f"{self.user.username} - {self.uploaded_at}"

class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    report = models.ForeignKey(UploadedReport, on_delete=models.CASCADE)
    question = models.TextField()
    answer = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.report.file.name} - {self.timestamp}"

class HealthData(models.Model):
    patient_id = models.CharField(max_length=100)
    report_date = models.DateField()
    parameter = models.CharField(max_length=100)
    value = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    report = models.ForeignKey('UploadedReport', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.patient_id} - {self.parameter}: {self.value} {self.unit} ({self.report_date})"

    def summary(self):
        return f"{self.parameter}: {self.value} {self.unit} ({self.report_date})"
