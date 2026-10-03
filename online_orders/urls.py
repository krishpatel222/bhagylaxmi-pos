from django.urls import path
from . import views

app_name = 'online_orders'

urlpatterns = [
    path('online-orders/', views.order_list, name='list'),
    path('online-orders/add/', views.order_add, name='add'),
    path('online-orders/dispatch/', views.dispatch_dashboard, name='dispatch'),
    path('online-orders/<int:pk>/', views.order_detail, name='detail'),
    path('online-orders/<int:pk>/edit/', views.order_edit, name='edit'),
    path('online-orders/<int:pk>/status/', views.order_status_change, name='status_change'),
    path('online-orders/<int:pk>/label/', views.order_shipping_label, name='shipping_label'),
    path('online-orders/<int:pk>/delete/', views.order_delete, name='delete'),
]
