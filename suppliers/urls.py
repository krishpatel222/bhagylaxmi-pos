from django.urls import path
from . import views

app_name = 'suppliers'

urlpatterns = [
    path('suppliers/', views.supplier_list, name='list'),
    path('suppliers/add/', views.supplier_add, name='add'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='detail'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit, name='edit'),
    path('suppliers/<int:pk>/toggle/', views.supplier_toggle_status, name='toggle_status'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete, name='delete'),
]
