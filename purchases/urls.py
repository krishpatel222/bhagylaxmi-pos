from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    path('purchases/', views.purchase_list, name='list'),
    path('purchases/add/', views.purchase_add, name='add'),
    path('purchases/<int:pk>/', views.purchase_detail, name='detail'),
    path('purchases/<int:pk>/delete/', views.purchase_delete, name='delete'),
]
