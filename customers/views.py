from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from accounts.decorators import admin_required, cashier_or_admin_required
from .models import Customer
from .forms import CustomerForm, CashierCustomerForm


@cashier_or_admin_required
def customer_list(request):
    """
    Customer Directory View.
    Accessible by both Admin and Cashier.
    Financial metrics (opening balance) are strictly hidden for Cashier.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    city_filter = request.GET.get('city', '').strip()

    customers = Customer.objects.all()

    # Cashier sees only active customers by default unless searching
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier
    if is_cashier and not status_filter:
        customers = customers.filter(is_active=True)

    if query:
        customers = customers.filter(
            models.Q(name__icontains=query) |
            models.Q(customer_id__icontains=query) |
            models.Q(mobile__icontains=query) |
            models.Q(whatsapp__icontains=query) |
            models.Q(email__icontains=query) |
            models.Q(gst_number__icontains=query) |
            models.Q(city__icontains=query)
        )

    if status_filter == 'active':
        customers = customers.filter(is_active=True)
    elif status_filter == 'inactive':
        customers = customers.filter(is_active=False)

    if city_filter:
        customers = customers.filter(city__iexact=city_filter)

    cities = Customer.objects.values_list('city', flat=True).distinct().exclude(city__isnull=True).exclude(city__exact='')

    paginator = Paginator(customers, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'customers': page_obj.object_list,
        'cities': cities,
        'query': query,
        'status_filter': status_filter,
        'city_filter': city_filter,
        'is_cashier': is_cashier,
    }
    return render(request, 'customers/customer_list.html', context)


@cashier_or_admin_required
def customer_add(request):
    """
    Add Customer View.
    Cashiers use CashierCustomerForm (excluding opening_balance).
    Admins use CustomerForm.
    """
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier

    if request.method == 'POST':
        form_class = CashierCustomerForm if is_cashier else CustomerForm
        form = form_class(request.POST)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile')
            if mobile:
                dup = Customer.objects.filter(mobile=mobile).first()
                if dup:
                    messages.warning(request, f"Warning: Customer '{dup.name}' ({dup.customer_id}) already has mobile number {mobile}.")
            customer = form.save()
            messages.success(request, f"Customer '{customer.name}' ({customer.customer_id}) registered successfully!")
            return redirect('customers:list')
        else:
            messages.error(request, "Please fix the errors in the customer form below.")
    else:
        form_class = CashierCustomerForm if is_cashier else CustomerForm
        form = form_class()

    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': 'Add New Customer / નવો ગ્રાહક',
        'is_cashier': is_cashier
    })


@cashier_or_admin_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier
    
    # Query customer sales history (STEP 11)
    sales_qs = customer.sales.select_related('created_by').all()
    if is_cashier:
        sales_qs = sales_qs.filter(created_by=request.user)
    sales_history = list(sales_qs.order_by('-created_at'))
    
    context = {
        'customer': customer,
        'sales_history': sales_history,
        'is_cashier': is_cashier
    }
    return render(request, 'customers/customer_detail.html', context)


@cashier_or_admin_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier

    if request.method == 'POST':
        form_class = CashierCustomerForm if is_cashier else CustomerForm
        form = form_class(request.POST, instance=customer)
        if form.is_valid():
            mobile = form.cleaned_data.get('mobile')
            if mobile:
                dup = Customer.objects.filter(mobile=mobile).exclude(pk=customer.pk).first()
                if dup:
                    messages.warning(request, f"Warning: Customer '{dup.name}' ({dup.customer_id}) already has mobile number {mobile}.")
            form.save()
            messages.success(request, f"Customer '{customer.name}' ({customer.customer_id}) updated successfully!")
            return redirect('customers:list')
        else:
            messages.error(request, "Please fix the errors in the customer form below.")
    else:
        form_class = CashierCustomerForm if is_cashier else CustomerForm
        form = form_class(instance=customer)

    return render(request, 'customers/customer_form.html', {
        'form': form,
        'title': f"Edit Customer: {customer.name} ({customer.customer_id})",
        'customer': customer,
        'is_cashier': is_cashier
    })


@admin_required
@require_POST
def customer_toggle_status(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = not customer.is_active
    customer.save()
    status_str = "activated" if customer.is_active else "deactivated"
    messages.success(request, f"Customer '{customer.name}' has been {status_str}.")
    return redirect('customers:list')


@admin_required
@require_POST
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    
    # Check if future sales reference this customer (Step 11)
    has_sales = hasattr(customer, 'sales') and customer.sales.exists()
    
    if has_sales:
        messages.error(request, f"Cannot delete customer '{customer.name}' because purchase/sales history exists. Please deactivate instead.")
    else:
        name = customer.name
        cid = customer.customer_id
        customer.delete()
        messages.success(request, f"Customer '{name}' ({cid}) deleted successfully.")

    return redirect('customers:list')


@cashier_or_admin_required
def customer_search_json(request):
    """
    Reusable Customer Selector Endpoint for POS billing (Step 10 preparation).
    Returns JSON list of active customers matching search query.
    NO financial data is included in response.
    """
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        customers = Customer.objects.filter(is_active=True).filter(
            models.Q(name__icontains=q) |
            models.Q(mobile__icontains=q) |
            models.Q(customer_id__icontains=q)
        )[:10]
        for c in customers:
            results.append({
                'id': c.id,
                'customer_id': c.customer_id,
                'name': c.name,
                'mobile': c.mobile,
                'city': c.city or ''
            })
    return JsonResponse({'customers': results})
