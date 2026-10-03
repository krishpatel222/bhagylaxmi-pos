from django.urls import path
from . import views

urlpatterns = [
    # Category URLs
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/toggle/', views.category_toggle, name='category_toggle'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Brand URLs
    path('brands/', views.brand_list, name='brand_list'),
    path('brands/add/', views.brand_add, name='brand_add'),
    path('brands/<int:pk>/edit/', views.brand_edit, name='brand_edit'),
    path('brands/<int:pk>/toggle/', views.brand_toggle, name='brand_toggle'),
    path('brands/<int:pk>/delete/', views.brand_delete, name='brand_delete'),
]
