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
    path('extracted-health-data/', views.extracted_health_data, name='extracted_health_data'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('signup/', views.user_signup, name='signup'),
    path('profile/', views.user_profile, name='profile'),
    path('translate-summary/', views.translate_summary, name='translate_summary'),
    path('chatbot/ask/', chatbot_ask, name='chatbot_ask'),
]
