from django.urls import path
from . import views

app_name = 'expenses'

urlpatterns = [
    path('expenses/', views.expense_list, name='list'),
    path('expenses/add/', views.expense_create, name='create'),
    path('expenses/<str:expense_id>/', views.expense_detail, name='detail'),
    path('expenses/<str:expense_id>/edit/', views.expense_edit, name='edit'),
    path('expenses/<str:expense_id>/delete/', views.expense_delete, name='delete'),
]
