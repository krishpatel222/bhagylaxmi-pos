from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('reports/', views.reports_dashboard, name='dashboard'),
    path('reports/sales/', views.sales_report, name='sales'),
    path('reports/profit/', views.profit_report, name='profit'),
    path('reports/purchases/', views.purchases_report, name='purchases'),
    path('reports/inventory/', views.inventory_report, name='inventory'),
    path('reports/expenses/', views.expenses_report, name='expenses'),
    path('reports/customers/', views.customers_report, name='customers'),
    path('reports/suppliers/', views.suppliers_report, name='suppliers'),
    path('reports/online-orders/', views.online_orders_report, name='online_orders'),
    path('reports/returns/', views.returns_report, name='returns'),
]
