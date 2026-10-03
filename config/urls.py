from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('accounts.urls')),  # Includes login/logout at top-level /login/ & /logout/
    path('', include('categories.urls')),
    path('', include('products.urls')),
    path('', include('inventory.urls')),
    path('', include('suppliers.urls')),
    path('', include('purchases.urls')),
    path('', include('customers.urls')),
    path('', include('sales.urls')),
    path('', include('online_orders.urls')),
    path('', include('expenses.urls')),
    path('', include('returns.urls')),
    path('', include('reports.urls')),
    path('', include('audit_log.urls')),
    path('', include('core.urls')),
]

handler403 = 'core.views.custom_permission_denied_view'
handler404 = 'core.views.custom_page_not_found_view'
handler500 = 'core.views.custom_server_error_view'

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)