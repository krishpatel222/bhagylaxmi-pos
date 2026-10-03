from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    path('customers/', views.customer_list, name='list'),
    path('customers/add/', views.customer_add, name='add'),
    path('customers/search/', views.customer_search_json, name='search_json'),
    path('customers/<int:pk>/', views.customer_detail, name='detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='edit'),
    path('customers/<int:pk>/toggle-status/', views.customer_toggle_status, name='toggle_status'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='delete'),
]
