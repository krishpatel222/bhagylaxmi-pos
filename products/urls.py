from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/toggle/', views.product_toggle, name='product_toggle'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('barcodes/', views.barcode_list, name='barcode_list'),
    path('products/<int:pk>/barcode/generate/', views.generate_barcode, name='generate_barcode'),
    path('products/<int:pk>/barcode/print/', views.barcode_print, name='barcode_print'),
]
