from django import forms
from analyzer.models import UploadedReport


class SymptomCheckerForm(forms.Form):
    symptoms = forms.CharField(
        label='Enter your symptoms (comma separated)',
        widget=forms.TextInput(attrs={
            'placeholder': 'e.g. fever, cough, headache',
            'class': 'form-control'
        })
    )

class ReportUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedReport
        fields = ['file']
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
        }

# Medical image annotation form
class MedicalImageUploadForm(forms.Form):
    image = forms.ImageField(label='Upload Medical Image', required=True)
    prompt = forms.CharField(
        label='Describe what you want to see or explain',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Explain this X-ray, Generate image of healthy lung'})
    )
