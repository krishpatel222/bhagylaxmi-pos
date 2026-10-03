from django.urls import path
from . import views

app_name = 'returns'

urlpatterns = [
    path('returns/', views.return_list, name='list'),
    path('returns/add/', views.return_create, name='create'),
    path('returns/<str:return_id>/', views.return_detail, name='detail'),
]
