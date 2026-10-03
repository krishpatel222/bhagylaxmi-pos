from django.urls import path
from . import views, backup

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    path('pos/', views.pos_billing_placeholder, name='pos_billing'),
    path('settings/shop/', views.shop_settings_view, name='shop_settings'),
    path('settings/backup/', backup.backup_dashboard, name='backup_dashboard'),
    path('settings/backup/download/<str:filename>/', backup.backup_download, name='backup_download'),
]