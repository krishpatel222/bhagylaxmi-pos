from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Q
from django.core.paginator import Paginator

from accounts.decorators import cashier_or_admin_required
from sales.models import Sale, SaleItem
from inventory.services import change_stock
from inventory.models import InventoryTransaction
from .models import SalesReturn, SalesReturnItem


@cashier_or_admin_required
def return_list(request):
    """
    List sales returns with search and pagination.
    """
    qs = SalesReturn.objects.select_related('sale', 'customer', 'created_by').all()

    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(return_id__icontains=q) |
            Q(sale__sale_id__icontains=q) |
            Q(customer__name__icontains=q) |
            Q(reason__icontains=q)
        )

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        qs = qs.filter(return_date__gte=date_from)
    if date_to:
        qs = qs.filter(return_date__lte=date_to)

    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'returns': page_obj,
        'page_obj': page_obj,
        'q': q,
        'date_from': date_from,
        'date_to': date_to,
    }
    return render(request, 'returns/return_list.html', context)


@cashier_or_admin_required
def return_create(request):
    """
    Process a sale return against an existing Sale.
    Query parameter: ?sale_id=SAL-000001
    """
    sale_id = request.GET.get('sale_id', '').strip() or request.POST.get('sale_id', '').strip()
    sale = None
    sale_items_data = []

    if sale_id:
        sale = Sale.objects.filter(sale_id=sale_id).prefetch_related('items__product').first()
        if sale:
            # Calculate remaining returnable quantities for each sale item
            for item in sale.items.all():
                already_returned = SalesReturnItem.objects.filter(
                    sales_return__sale=sale, product=item.product
                ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

                max_returnable = item.quantity - already_returned
                sale_items_data.append({
                    'item': item,
                    'already_returned': already_returned,
                    'max_returnable': max_returnable,
                })

    if request.method == 'POST' and sale:
        reason = request.POST.get('reason', '').strip()
        notes = request.POST.get('notes', '').strip()

        if not reason:
            messages.error(request, "Return reason is required.")
            return render(request, 'returns/return_form.html', {'sale': sale, 'sale_items_data': sale_items_data})

        items_to_return = []
        total_refund = Decimal('0.00')

        # Parse submitted quantities per product
        for item_info in sale_items_data:
            item = item_info['item']
            qty_str = request.POST.get(f'qty_{item.id}', '0').strip()
            try:
                ret_qty = Decimal(qty_str)
            except Exception:
                ret_qty = Decimal('0.00')

            if ret_qty > Decimal('0.00'):
                if ret_qty > item_info['max_returnable']:
                    messages.error(
                        request,
                        f"Cannot return {ret_qty} of '{item.product.name}'. Maximum returnable quantity is {item_info['max_returnable']}."
                    )
                    return render(request, 'returns/return_form.html', {'sale': sale, 'sale_items_data': sale_items_data})

                # Calculate item refund amount based on selling price
                item_refund = ret_qty * item.selling_price
                total_refund += item_refund
                items_to_return.append((item.product, ret_qty, item_refund))

        if not items_to_return:
            messages.error(request, "Please enter at least one item quantity to return.")
            return render(request, 'returns/return_form.html', {'sale': sale, 'sale_items_data': sale_items_data})

        # Atomic transaction: Create return record, return items, and restore inventory stock
        try:
            with transaction.atomic():
                sales_return = SalesReturn.objects.create(
                    sale=sale,
                    customer=sale.customer,
                    reason=reason,
                    refund_amount=total_refund,
                    notes=notes,
                    created_by=request.user,
                )

                for product, qty, refund in items_to_return:
                    SalesReturnItem.objects.create(
                        sales_return=sales_return,
                        product=product,
                        quantity=qty,
                        refund_amount=refund
                    )

                    # Restore stock using existing inventory service (SALES_RETURN)
                    change_stock(
                        product=product,
                        quantity=qty,
                        transaction_type=InventoryTransaction.TYPE_SALES_RETURN,
                        user=request.user,
                        reference_type='SALES_RETURN',
                        reference_id=sales_return.return_id,
                        note=f"Returned from Sale {sale.sale_id}: {reason}"
                    )

            messages.success(request, f"Sales Return {sales_return.return_id} processed successfully! Refund Amount: ₹{total_refund}")
            return redirect('returns:detail', return_id=sales_return.return_id)

        except Exception as e:
            messages.error(request, f"Error processing return: {str(e)}")

    return render(request, 'returns/return_form.html', {
        'sale': sale,
        'sale_id': sale_id,
        'sale_items_data': sale_items_data
    })


@cashier_or_admin_required
def return_detail(request, return_id):
    """
    View return details. Strictly excludes purchase prices / profit metrics.
    """
    sales_return = get_object_or_404(
        SalesReturn.objects.select_related('sale', 'customer', 'created_by').prefetch_related('items__product'),
        return_id=return_id
    )
    return render(request, 'returns/return_detail.html', {'sales_return': sales_return})
