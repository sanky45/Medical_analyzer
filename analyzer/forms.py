from django import forms
from .models import UploadedReport

class ReportUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedReport
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
        }
