

from django.urls import path
from . import views
from .utils import chatbot_ask

app_name = 'analyzer'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('upload/', views.upload_report, name='upload_report'),
    path('uploaded-reports/', views.uploaded_reports, name='uploaded_reports'),
    path('delete-report/<int:report_id>/', views.delete_report, name='delete_report'),
    path('analyze/', views.analyze_report, name='analyze_report'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('signup/', views.user_signup, name='signup'),
    path('profile/', views.user_profile, name='profile'),
    path('chatbot/ask/', chatbot_ask, name='chatbot_ask'),
    path('health-data-trends/', views.health_data_trends, name='health_data_trends'),
    path('extracted-key-parameters/', views.extracted_key_parameters, name='extracted_key_parameters'),
    path('analyze-profile/', views.analyze_profile, name='analyze_profile'),
    path('chatbot-widget/', views.chatbot_widget, name='chatbot_widget'),
    path('symptom-checker/', views.symptom_checker, name='symptom_checker'),
    path('medical-image-annotation/', views.medical_image_annotation, name='medical_image_annotation'),
]
