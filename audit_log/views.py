from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q

from accounts.decorators import admin_required
from .models import AuditLog


@admin_required
def audit_log_list(request):
    """
    Admin-only Audit Log Viewer.
    Strictly read-only with search, filtering, and pagination (25 items/page).
    Cashiers trying to access this view get 403 Forbidden.
    """
    qs = AuditLog.objects.select_related('user').all()

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(description__icontains=q) |
            Q(object_id__icontains=q) |
            Q(user__username__icontains=q)
        )

    # Action filter
    action = request.GET.get('action', '').strip()
    if action:
        qs = qs.filter(action=action)

    # Model filter
    model_name = request.GET.get('model_name', '').strip()
    if model_name:
        qs = qs.filter(model_name__icontains=model_name)

    # Date filter
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)

    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'logs': page_obj,
        'page_obj': page_obj,
        'actions': AuditLog.ACTION_CHOICES,
        'q': q,
        'action': action,
        'model_name': model_name,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'audit_log/audit_log_list.html', context)
