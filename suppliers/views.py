from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from accounts.decorators import admin_required
from .models import Supplier
from .forms import SupplierForm


@admin_required
def supplier_list(request):
    """
    Admin Supplier Directory View.
    Allows searching by ID, Name, Company, Mobile, or GST number,
    filtering by status and city, and paginating results.
    Strictly protected by @admin_required decorator.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    city_filter = request.GET.get('city', '').strip()

    suppliers = Supplier.objects.all()

    if query:
        suppliers = suppliers.filter(
            models.Q(name__icontains=query) |
            models.Q(company_name__icontains=query) |
            models.Q(supplier_id__icontains=query) |
            models.Q(mobile__icontains=query) |
            models.Q(gst_number__icontains=query)
        )

    if status_filter == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif status_filter == 'inactive':
        suppliers = suppliers.filter(is_active=False)

    if city_filter:
        suppliers = suppliers.filter(city__iexact=city_filter)

    # Distinct cities list for filter dropdown
    cities = Supplier.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city__exact='')

    paginator = Paginator(suppliers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'suppliers': page_obj.object_list,
        'cities': cities,
        'query': query,
        'status_filter': status_filter,
        'city_filter': city_filter,
    }
    return render(request, 'suppliers/supplier_list.html', context)


@admin_required
def supplier_add(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save()
            messages.success(request, f"Supplier '{supplier.name}' ({supplier.supplier_id}) added successfully!")
            return redirect('suppliers:list')
        else:
            messages.error(request, "Please correct the errors in the supplier form below.")
    else:
        form = SupplierForm()

    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': 'Add New Supplier / નવો સપ્લાયર'
    })


@admin_required
def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    purchases = supplier.purchases.select_related('created_by').order_by('-created_at') if hasattr(supplier, 'purchases') else []
    return render(request, 'suppliers/supplier_detail.html', {
        'supplier': supplier,
        'purchases': purchases,
    })


@admin_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f"Supplier '{supplier.name}' ({supplier.supplier_id}) updated successfully!")
            return redirect('suppliers:list')
        else:
            messages.error(request, "Please correct the errors in the supplier form below.")
    else:
        form = SupplierForm(instance=supplier)

    return render(request, 'suppliers/supplier_form.html', {
        'form': form,
        'title': f"Edit Supplier: {supplier.name} ({supplier.supplier_id})",
        'supplier': supplier
    })


@admin_required
@require_POST
def supplier_toggle_status(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not supplier.is_active
    supplier.save()
    status_str = "activated" if supplier.is_active else "deactivated"
    messages.success(request, f"Supplier '{supplier.name}' has been {status_str}.")
    return redirect('suppliers:list')


@admin_required
@require_POST
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    
    # Check if purchases reference this supplier in future Step 8
    has_purchases = hasattr(supplier, 'purchases') and supplier.purchases.exists()
    
    if has_purchases:
        messages.error(request, f"Cannot delete supplier '{supplier.name}' because purchase records exist for this supplier. Please deactivate instead.")
    else:
        name = supplier.name
        sid = supplier.supplier_id
        supplier.delete()
        messages.success(request, f"Supplier '{name}' ({sid}) deleted successfully.")

    return redirect('suppliers:list')
