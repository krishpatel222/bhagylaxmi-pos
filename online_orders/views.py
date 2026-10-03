import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models, transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.core.paginator import Paginator
from django.utils import timezone

from accounts.decorators import admin_required, cashier_or_admin_required
from products.models import Product
from customers.models import Customer
from inventory.models import InventoryTransaction
from inventory.services import change_stock
from .models import OnlineOrder, OnlineOrderItem
from .forms import OnlineOrderForm


@cashier_or_admin_required
def order_list(request):
    """
    Online Orders Directory view.
    Multi-criteria searching and filtering with pagination.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment_status', '')
    courier_filter = request.GET.get('courier', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    orders_qs = OnlineOrder.objects.select_related('customer', 'created_by').all()

    if query:
        orders_qs = orders_qs.filter(
            models.Q(order_id__icontains=query) |
            models.Q(customer_name__icontains=query) |
            models.Q(mobile__icontains=query) |
            models.Q(pincode__icontains=query) |
            models.Q(tracking_number__icontains=query)
        )

    if status_filter:
        orders_qs = orders_qs.filter(status=status_filter)

    if payment_filter:
        orders_qs = orders_qs.filter(payment_status=payment_filter)

    if courier_filter:
        orders_qs = orders_qs.filter(courier_name__icontains=courier_filter)

    if date_from:
        orders_qs = orders_qs.filter(order_date__date__gte=date_from)

    if date_to:
        orders_qs = orders_qs.filter(order_date__date__lte=date_to)

    paginator = Paginator(orders_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier

    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'query': query,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'courier_filter': courier_filter,
        'date_from': date_from,
        'date_to': date_to,
        'is_cashier': is_cashier,
    }
    return render(request, 'online_orders/order_list.html', context)


@cashier_or_admin_required
def order_add(request):
    """
    Manually Enter New Online Order.
    Calculates order total, payment received, and pending amount server-side.
    """
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier
    products = Product.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        form = OnlineOrderForm(request.POST)
        items_json = request.POST.get('items_json', '[]')
        try:
            items_data = json.loads(items_json)
        except Exception:
            items_data = []

        if form.is_valid():
            if not items_data:
                messages.error(request, "Please add at least one product to the online order.")
            else:
                try:
                    with transaction.atomic():
                        order = form.save(commit=False)
                        order.created_by = request.user
                        
                        # Server-side order total calculation
                        calculated_total = Decimal('0.00')
                        items_to_create = []

                        for item in items_data:
                            product_id = item.get('product_id')
                            qty = Decimal(str(item.get('quantity', '1')))
                            if qty <= Decimal('0.00'):
                                raise ValueError("Product quantity must be greater than zero.")
                            
                            product = Product.objects.get(pk=product_id, is_active=True)
                            selling_price = Decimal(str(product.selling_price))
                            line_total = (selling_price * qty).quantize(Decimal('0.01'))
                            calculated_total += line_total

                            items_to_create.append({
                                'product': product,
                                'quantity': qty,
                                'selling_price': selling_price,
                                'line_total': line_total
                            })

                        order.order_amount = calculated_total
                        
                        # Server-side payment calculation
                        pay_received = order.payment_received or Decimal('0.00')
                        if pay_received > calculated_total:
                            pay_received = calculated_total
                        
                        order.payment_received = pay_received
                        order.pending_amount = calculated_total - pay_received

                        if pay_received == calculated_total:
                            order.payment_status = OnlineOrder.PAYMENT_STATUS_PAID
                        elif pay_received == Decimal('0.00') and order.payment_status != OnlineOrder.PAYMENT_STATUS_COD:
                            order.payment_status = OnlineOrder.PAYMENT_STATUS_PENDING
                        elif Decimal('0.00') < pay_received < calculated_total:
                            order.payment_status = OnlineOrder.PAYMENT_STATUS_PARTIAL

                        order.save()

                        # Save items
                        for item_info in items_to_create:
                            OnlineOrderItem.objects.create(
                                order=order,
                                product=item_info['product'],
                                quantity=item_info['quantity'],
                                selling_price=item_info['selling_price'],
                                line_total=item_info['line_total']
                            )

                        messages.success(request, f"Online Order '{order.order_id}' for {order.customer_name} created successfully!")
                        return redirect('online_orders:detail', pk=order.pk)

                except Exception as e:
                    messages.error(request, f"Order creation failed: {str(e)}")
        else:
            messages.error(request, "Please correct the errors in the form below.")
    else:
        form = OnlineOrderForm()

    return render(request, 'online_orders/order_form.html', {
        'form': form,
        'products': products,
        'title': 'Create Online Order / નવો ઓનલાઇન ઓર્ડર',
        'is_cashier': is_cashier
    })


@cashier_or_admin_required
def order_detail(request, pk):
    """
    Online Order Detail view.
    """
    order = get_object_or_404(OnlineOrder.objects.select_related('customer', 'created_by').prefetch_related('items__product'), pk=pk)
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier

    context = {
        'order': order,
        'items': order.items.all(),
        'is_cashier': is_cashier
    }
    return render(request, 'online_orders/order_detail.html', context)


@cashier_or_admin_required
def order_edit(request, pk):
    """
    Edit Online Order Information.
    """
    order = get_object_or_404(OnlineOrder, pk=pk)
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier

    if request.method == 'POST':
        form = OnlineOrderForm(request.POST, instance=order)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                pay_received = order.payment_received or Decimal('0.00')
                order.pending_amount = order.order_amount - pay_received
                
                if pay_received == order.order_amount:
                    order.payment_status = OnlineOrder.PAYMENT_STATUS_PAID
                elif pay_received == Decimal('0.00') and order.payment_status != OnlineOrder.PAYMENT_STATUS_COD:
                    order.payment_status = OnlineOrder.PAYMENT_STATUS_PENDING
                elif Decimal('0.00') < pay_received < order.order_amount:
                    order.payment_status = OnlineOrder.PAYMENT_STATUS_PARTIAL

                order.save()
                messages.success(request, f"Online Order '{order.order_id}' updated successfully!")
                return redirect('online_orders:detail', pk=order.pk)
        else:
            messages.error(request, "Please fix errors in the form below.")
    else:
        form = OnlineOrderForm(instance=order)

    return render(request, 'online_orders/order_form.html', {
        'form': form,
        'order': order,
        'title': f"Edit Order: {order.order_id}",
        'is_cashier': is_cashier
    })


@cashier_or_admin_required
@require_POST
def order_status_change(request, pk):
    """
    Update Online Order Status (POST + CSRF).
    Handles dispatch status change & triggers atomic stock reduction via inventory service.
    """
    order = get_object_or_404(OnlineOrder, pk=pk)
    new_status = request.POST.get('status', '').strip().upper()
    courier = request.POST.get('courier_name', '').strip()
    tracking = request.POST.get('tracking_number', '').strip()

    valid_statuses = [choice[0] for choice in OnlineOrder.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, f"Invalid status '{new_status}'.")
        return redirect('online_orders:detail', pk=order.pk)

    try:
        with transaction.atomic():
            prev_status = order.status

            if courier:
                order.courier_name = courier
            if tracking:
                order.tracking_number = tracking

            # Transitioning to DISPATCHED
            if new_status == OnlineOrder.STATUS_DISPATCHED:
                if not order.dispatch_date:
                    order.dispatch_date = timezone.now()
                
                # Perform stock OUT if not previously dispatched
                if prev_status != OnlineOrder.STATUS_DISPATCHED:
                    for item in order.items.select_related('product'):
                        change_stock(
                            product=item.product,
                            quantity=item.quantity,
                            transaction_type=InventoryTransaction.TYPE_SALE_OUT,
                            user=request.user,
                            reference_type='ONLINE_ORDER',
                            reference_id=str(order.id),
                            note=f"Dispatched Order {order.order_id}"
                        )

            order.status = new_status
            order.save()

            messages.success(request, f"Order '{order.order_id}' status updated to '{order.get_status_display()}'.")

    except Exception as e:
        messages.error(request, f"Status update failed: {str(e)}")

    return redirect('online_orders:detail', pk=order.pk)


@cashier_or_admin_required
def order_shipping_label(request, pk):
    """
    CUSTOMER & COURIER FACING SHIPPING LABEL (STEP 13).
    STRICT PRIVACY GUARANTEE:
    This endpoint and template context MUST NOT contain or leak:
    - Order Amount
    - Payment Received
    - Pending Amount
    - Payment Status
    - Purchase Price
    - Cost Price
    - Profit
    - Supplier data
    - Internal Notes
    """
    order = get_object_or_404(OnlineOrder.objects.prefetch_related('items__product'), pk=pk)

    # Safe item descriptions without any price or cost details
    safe_items = []
    for item in order.items.all():
        safe_items.append({
            'product_name': item.product.name,
            'gujarati_name': item.product.gujarati_name or '',
            'quantity': item.quantity,
            'unit': item.product.unit
        })

    # Customer/Shipping Context ONLY
    context = {
        'order_id': order.order_id,
        'customer_name': order.customer_name,
        'mobile': order.mobile,
        'whatsapp': order.whatsapp or '',
        'full_address': order.full_address,
        'city': order.city,
        'state': order.state,
        'pincode': order.pincode,
        'courier_name': order.courier_name or 'Standard Courier',
        'tracking_number': order.tracking_number or '-',
        'order_date': order.order_date,
        'safe_items': safe_items,
        'shop_name': "ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ",
        'shop_address': "જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત",
        'shop_phone': "+91 98765 43210",
    }
    return render(request, 'online_orders/shipping_label.html', context)


@cashier_or_admin_required
def dispatch_dashboard(request):
    """
    Operational Dispatch Queue.
    Displays orders in CONFIRMED, PACKED, or DISPATCHED status for easy packing & shipping label printing.
    """
    orders = OnlineOrder.objects.filter(
        status__in=[OnlineOrder.STATUS_CONFIRMED, OnlineOrder.STATUS_PACKED, OnlineOrder.STATUS_DISPATCHED]
    ).order_by('-order_date')

    return render(request, 'online_orders/dispatch.html', {'orders': orders})


@admin_required
@require_POST
def order_delete(request, pk):
    """
    Admin-only Order Delete endpoint.
    """
    order = get_object_or_404(OnlineOrder, pk=pk)
    oid = order.order_id
    order.delete()
    messages.success(request, f"Online Order '{oid}' deleted successfully.")
    return redirect('online_orders:list')
