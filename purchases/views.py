from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models, transaction
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError

from accounts.decorators import admin_required
from suppliers.models import Supplier
from products.models import Product
from inventory.services import change_stock
from .models import Purchase, PurchaseItem
from .forms import PurchaseForm


@admin_required
def purchase_list(request):
    """
    Admin Purchase Invoices List.
    Shows supplier invoices, grand totals, payment statuses, and posted stock statuses.
    Strictly protected by @admin_required decorator.
    """
    query = request.GET.get('q', '').strip()
    supplier_id = request.GET.get('supplier', '')
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    purchases = Purchase.objects.select_related('supplier', 'created_by').prefetch_related('items__product').all()

    if query:
        purchases = purchases.filter(
            models.Q(purchase_id__icontains=query) |
            models.Q(supplier__name__icontains=query) |
            models.Q(supplier__company_name__icontains=query) |
            models.Q(invoice_number__icontains=query) |
            models.Q(items__product__name__icontains=query)
        ).distinct()

    if supplier_id.isdigit():
        purchases = purchases.filter(supplier_id=int(supplier_id))

    if status_filter:
        purchases = purchases.filter(payment_status=status_filter)

    if date_from:
        purchases = purchases.filter(purchase_date__date__gte=date_from)
    if date_to:
        purchases = purchases.filter(purchase_date__date__lte=date_to)

    paginator = Paginator(purchases, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    suppliers = Supplier.objects.filter(is_active=True)

    context = {
        'page_obj': page_obj,
        'purchases': page_obj.object_list,
        'suppliers': suppliers,
        'query': query,
        'supplier_id': supplier_id,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': Purchase.PAYMENT_STATUS_CHOICES,
    }
    return render(request, 'purchases/purchase_list.html', context)


@admin_required
def purchase_add(request):
    """
    Admin Purchase Creation View with Dynamic Items & Atomic Stock Posting.
    """
    products = Product.objects.filter(is_active=True).select_related('category')

    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        
        # Read items arrays submitted from dynamic table rows
        product_ids = request.POST.getlist('product_id[]')
        quantities = request.POST.getlist('quantity[]')
        purchase_prices = request.POST.getlist('purchase_price[]')
        gst_rates = request.POST.getlist('gst_rate[]')
        discounts = request.POST.getlist('discount[]')

        if form.is_valid():
            if not product_ids or len(product_ids) == 0:
                messages.error(request, "Please add at least one product item to the purchase invoice.")
            else:
                try:
                    with transaction.atomic():
                        # 1. Create Purchase Header Instance (unposted stock)
                        purchase = form.save(commit=False)
                        purchase.created_by = request.user
                        purchase.stock_posted = False
                        purchase.save()

                        running_subtotal = Decimal('0.00')
                        running_gst = Decimal('0.00')
                        running_discount = Decimal('0.00')

                        # 2. Process Purchase Items & Stock Increases
                        for i in range(len(product_ids)):
                            pid = product_ids[i]
                            if not pid:
                                continue
                            
                            product = Product.objects.get(pk=pid)
                            qty = Decimal(str(quantities[i] or '0'))
                            price = Decimal(str(purchase_prices[i] or '0'))
                            gst_rate = Decimal(str(gst_rates[i] or '0'))
                            disc = Decimal(str(discounts[i] or '0'))

                            if qty <= 0:
                                raise ValidationError(f"Quantity for product '{product.name}' must be greater than zero.")
                            if price < 0:
                                raise ValidationError(f"Purchase price for product '{product.name}' cannot be negative.")

                            item = PurchaseItem(
                                purchase=purchase,
                                product=product,
                                quantity=qty,
                                purchase_price=price,
                                gst_rate=gst_rate,
                                discount=disc
                            )
                            item.save()

                            # Accumulate headers totals
                            running_subtotal += (qty * price)
                            running_discount += disc
                            running_gst += item.gst_amount

                            # 3. Post Stock Increase via Inventory Service (PURCHASE_IN)
                            change_stock(
                                product=product,
                                quantity=qty,
                                transaction_type='PURCHASE_IN',
                                user=request.user,
                                reference_type='PURCHASE',
                                reference_id=purchase.purchase_id,
                                note=f"Stock IN via Purchase Invoice {purchase.purchase_id} (Supplier: {purchase.supplier.name})"
                            )

                        # Finalize purchase financial totals & payment status
                        purchase.subtotal = running_subtotal
                        purchase.discount = running_discount
                        purchase.gst_amount = running_gst
                        purchase.grand_total = max(Decimal('0.00'), (running_subtotal - running_discount) + running_gst)

                        if purchase.paid_amount > purchase.grand_total:
                            raise ValidationError(f"Paid amount (₹{purchase.paid_amount}) cannot exceed grand total (₹{purchase.grand_total}).")

                        purchase.stock_posted = True
                        purchase.save()

                        messages.success(
                            request,
                            f"Purchase Invoice '{purchase.purchase_id}' created successfully! Stock has been updated for all items."
                        )
                        return redirect('purchases:detail', pk=purchase.pk)

                except ValidationError as ve:
                    messages.error(request, str(ve.message if hasattr(ve, 'message') else ve))
                except Exception as e:
                    messages.error(request, f"Error saving purchase: {str(e)}")
        else:
            messages.error(request, "Please fix the form errors below.")
    else:
        form = PurchaseForm()

    context = {
        'form': form,
        'products': products,
        'title': 'New Purchase Invoice / નવી ખરીદી'
    }
    return render(request, 'purchases/purchase_form.html', context)


@admin_required
def purchase_detail(request, pk):
    purchase = get_object_or_404(
        Purchase.objects.select_related('supplier', 'created_by').prefetch_related('items__product'),
        pk=pk
    )
    return render(request, 'purchases/purchase_detail.html', {'purchase': purchase})


@admin_required
@require_POST
def purchase_delete(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    
    # Strictly block deleting posted purchases to protect inventory and accounting integrity
    if purchase.stock_posted:
        messages.error(
            request,
            f"Purchase '{purchase.purchase_id}' has already been posted to inventory stock and cannot be deleted."
        )
    else:
        pid = purchase.purchase_id
        purchase.delete()
        messages.success(request, f"Unposted Purchase '{pid}' deleted successfully.")

    return redirect('purchases:list')
