from django.urls import path
from . import views

urlpatterns = [
    path('inventory/', views.inventory_dashboard, name='inventory_dashboard'),
    path('inventory/stock/', views.stock_list, name='stock_list'),
    path('inventory/history/', views.history_list, name='history_list'),
    path('inventory/adjust/', views.stock_adjust, name='stock_adjust'),
]
