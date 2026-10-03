from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('pos/', views.pos_billing, name='pos'),
    path('sales/api/products/search/', views.pos_product_search_json, name='product_search_json'),
    path('sales/checkout/', views.pos_checkout, name='checkout'),
    path('sales/<int:pk>/receipt/', views.pos_receipt, name='receipt'),
    path('sales/<int:pk>/invoice/', views.sale_invoice, name='invoice'),
    path('sales/', views.sale_list, name='list'),
    path('sales/<int:pk>/', views.sale_detail, name='detail'),
    path('sales/<int:pk>/edit/', views.sale_edit, name='edit'),
    path('sales/<int:pk>/delete/', views.sale_delete, name='delete'),
]
