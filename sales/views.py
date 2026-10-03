import json
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models, transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.core.paginator import Paginator

from accounts.decorators import admin_required, cashier_or_admin_required
from categories.models import Category
from products.models import Product
from customers.models import Customer
from inventory.models import InventoryTransaction
from inventory.services import change_stock
from .models import Sale, SaleItem


@cashier_or_admin_required
def pos_billing(request):
    """
    Main POS Billing Terminal Screen.
    Accessible by both Admin and Cashier.
    """
    categories = Category.objects.filter(is_active=True).order_by('name')
    is_cashier = hasattr(request.user, 'profile') and request.user.profile.is_cashier

    context = {
        'categories': categories,
        'is_cashier': is_cashier,
        'shop_name': "ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ",
        'shop_address': "જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત",
    }
    return render(request, 'sales/pos.html', context)


@cashier_or_admin_required
def pos_product_search_json(request):
    """
    Fast Product Search API for POS terminal.
    Searches active products by Name, Gujarati Name, SKU, Barcode, or Product ID.
    STRICTLY EXCLUDES purchase_price from JSON output.
    """
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '').strip()

    products_qs = Product.objects.filter(is_active=True)

    if category_id:
        products_qs = products_qs.filter(category_id=category_id)

    if q:
        products_qs = products_qs.filter(
            models.Q(name__icontains=q) |
            models.Q(gujarati_name__icontains=q) |
            models.Q(sku__icontains=q) |
            models.Q(barcode__icontains=q) |
            models.Q(product_id__icontains=q)
        )

    products_qs = products_qs.select_related('category', 'brand')[:30]

    results = []
    for p in products_qs:
        results.append({
            'id': p.id,
            'product_id': p.product_id,
            'name': p.name,
            'gujarati_name': p.gujarati_name or '',
            'sku': p.sku or '',
            'barcode': p.barcode or '',
            'selling_price': str(p.selling_price),
            'mrp': str(p.mrp) if p.mrp else str(p.selling_price),
            'gst_rate': str(p.gst_rate or '0.00'),
            'unit': p.unit,
            'current_stock': str(p.current_stock),
            'category_name': p.category.name if p.category else ''
        })

    return JsonResponse({'products': results})


@cashier_or_admin_required
@require_POST
@transaction.atomic
def pos_checkout(request):
    """
    Atomic POS Checkout Handler.
    Performs server-side validation, stock locks, sale & item creation,
    and automatic stock reduction via inventory service inside ONE transaction.
    """
    try:

        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        items_data = data.get('items', [])
        if isinstance(items_data, str):
            items_data = json.loads(items_data)

        if not items_data:
            return JsonResponse({'success': False, 'message': "Cart is empty. Please add products to complete sale."}, status=400)

        customer_id = data.get('customer_id')
        customer = None
        if customer_id:
            customer = Customer.objects.filter(pk=customer_id, is_active=True).first()

        payment_method = data.get('payment_method', Sale.PAYMENT_METHOD_CASH).upper()
        notes = data.get('notes', '').strip()
        overall_discount = Decimal(str(data.get('overall_discount', '0.00') or '0.00'))

        if overall_discount < 0:
            return JsonResponse({'success': False, 'message': "Discount cannot be negative."}, status=400)

        calculated_subtotal = Decimal('0.00')
        calculated_gst_total = Decimal('0.00')
        sale_items_to_create = []

        # 1. Lock Products & Validate Stock Atomically
        for item in items_data:
            product_pk = item.get('product_id')
            try:
                qty = Decimal(str(item.get('quantity', '0')))
            except Exception:
                return JsonResponse({'success': False, 'message': "Invalid item quantity."}, status=400)

            if qty <= 0:
                return JsonResponse({'success': False, 'message': "Product quantity must be greater than zero."}, status=400)

            # Lock product row using select_for_update()
            try:
                product = Product.objects.select_for_update().get(pk=product_pk, is_active=True)
            except Product.DoesNotExist:
                return JsonResponse({'success': False, 'message': f"Product ID {product_pk} not found or inactive."}, status=404)

            # Strict Stock Check
            if product.current_stock < qty:
                return JsonResponse({
                    'success': False,
                    'message': f"Insufficient stock for '{product.name}'. Current stock: {product.current_stock} {product.unit}, Requested: {qty} {product.unit}."
                }, status=400)

            item_discount = Decimal(str(item.get('discount', '0.00') or '0.00'))
            if item_discount < 0:
                return JsonResponse({'success': False, 'message': f"Discount for '{product.name}' cannot be negative."}, status=400)

            selling_price = Decimal(str(product.selling_price))
            mrp = Decimal(str(product.mrp)) if product.mrp else selling_price
            gst_rate = Decimal(str(product.gst_rate or '0.00'))

            raw_amount = (selling_price * qty) - item_discount
            if raw_amount < 0:
                return JsonResponse({'success': False, 'message': f"Discount for '{product.name}' exceeds item subtotal."}, status=400)

            item_gst = (raw_amount * gst_rate / Decimal('100.00')).quantize(Decimal('0.01'))
            line_total = (raw_amount + item_gst).quantize(Decimal('0.01'))

            calculated_subtotal += raw_amount
            calculated_gst_total += item_gst

            sale_items_to_create.append({
                'product': product,
                'quantity': qty,
                'selling_price': selling_price,
                'mrp': mrp,
                'gst_rate': gst_rate,
                'gst_amount': item_gst,
                'discount': item_discount,
                'line_total': line_total
            })

        # 2. Subtotal & Grand Total Calculation
        if overall_discount > calculated_subtotal:
            return JsonResponse({'success': False, 'message': "Bill discount cannot exceed subtotal amount."}, status=400)

        grand_total = (calculated_subtotal + calculated_gst_total - overall_discount).quantize(Decimal('0.01'))

        # 3. Payment Method & Amounts Server-side Calculation
        cash_amt = Decimal(str(data.get('cash_amount', '0.00') or '0.00'))
        upi_amt = Decimal(str(data.get('upi_amount', '0.00') or '0.00'))
        card_amt = Decimal(str(data.get('card_amount', '0.00') or '0.00'))
        bank_amt = Decimal(str(data.get('bank_transfer_amount', '0.00') or '0.00'))
        credit_amt = Decimal(str(data.get('credit_amount', '0.00') or '0.00'))

        if payment_method == Sale.PAYMENT_METHOD_CASH:
            paid_amount = grand_total
            pending_amount = Decimal('0.00')
            cash_amt = grand_total
            payment_status = Sale.PAYMENT_STATUS_PAID
        elif payment_method == Sale.PAYMENT_METHOD_UPI:
            paid_amount = grand_total
            pending_amount = Decimal('0.00')
            upi_amt = grand_total
            payment_status = Sale.PAYMENT_STATUS_PAID
        elif payment_method == Sale.PAYMENT_METHOD_CARD:
            paid_amount = grand_total
            pending_amount = Decimal('0.00')
            card_amt = grand_total
            payment_status = Sale.PAYMENT_STATUS_PAID
        elif payment_method == Sale.PAYMENT_METHOD_BANK:
            paid_amount = grand_total
            pending_amount = Decimal('0.00')
            bank_amt = grand_total
            payment_status = Sale.PAYMENT_STATUS_PAID
        elif payment_method == Sale.PAYMENT_METHOD_CREDIT:
            paid_amount = Decimal('0.00')
            pending_amount = grand_total
            credit_amt = grand_total
            payment_status = Sale.PAYMENT_STATUS_PENDING
        elif payment_method == Sale.PAYMENT_METHOD_MIXED:
            total_components = cash_amt + upi_amt + card_amt + bank_amt + credit_amt
            if total_components != grand_total:
                return JsonResponse({
                    'success': False,
                    'message': f"Mixed payment components (₹{total_components}) must equal Grand Total (₹{grand_total})."
                }, status=400)
            paid_amount = cash_amt + upi_amt + card_amt + bank_amt
            pending_amount = credit_amt
            if paid_amount == grand_total:
                payment_status = Sale.PAYMENT_STATUS_PAID
            elif paid_amount == Decimal('0.00'):
                payment_status = Sale.PAYMENT_STATUS_PENDING
            else:
                payment_status = Sale.PAYMENT_STATUS_PARTIAL
        else:
            paid_amount = grand_total
            pending_amount = Decimal('0.00')
            payment_status = Sale.PAYMENT_STATUS_PAID

        # 4. Create Sale Record
        sale = Sale.objects.create(
            customer=customer,
            subtotal=calculated_subtotal,
            discount=overall_discount,
            gst_amount=calculated_gst_total,
            grand_total=grand_total,
            payment_method=payment_method,
            paid_amount=paid_amount,
            pending_amount=pending_amount,
            payment_status=payment_status,
            cash_amount=cash_amt,
            upi_amount=upi_amt,
            card_amount=card_amt,
            bank_transfer_amount=bank_amt,
            credit_amount=credit_amt,
            notes=notes,
            created_by=request.user
        )

        # 5. Create SaleItems & Atomic Stock OUT
        for item_info in sale_items_to_create:
            SaleItem.objects.create(
                sale=sale,
                product=item_info['product'],
                quantity=item_info['quantity'],
                selling_price=item_info['selling_price'],
                mrp=item_info['mrp'],
                gst_rate=item_info['gst_rate'],
                gst_amount=item_info['gst_amount'],
                discount=item_info['discount'],
                line_total=item_info['line_total']
            )

            # Reduce stock via existing stock service (SALE_OUT)
            change_stock(
                product=item_info['product'],
                quantity=item_info['quantity'],
                transaction_type=InventoryTransaction.TYPE_SALE_OUT,
                user=request.user,
                reference_type='SALE',
                reference_id=str(sale.id),
                note=f"POS Sale {sale.sale_id}"
            )

        return JsonResponse({
            'success': True,
            'sale_id': sale.sale_id,
            'sale_pk': sale.pk,
            'grand_total': str(sale.grand_total),
            'receipt_url': reverse('sales:receipt', kwargs={'pk': sale.pk})
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f"Checkout error: {str(e)}"}, status=500)


@cashier_or_admin_required
def pos_receipt(request, pk):
    """
    Printable POS Bill Receipt (80mm & Standard Layout).
    Admins can view any sale receipt.
    Cashiers can view ONLY their own sale receipts.
    STRICTLY EXCLUDES purchase prices, profit, supplier data.
    """
    sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product'), pk=pk)
    
    is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin
    if not is_admin and sale.created_by != request.user:
        return HttpResponseForbidden("You are not authorized to view this bill receipt.")

    context = {
        'sale': sale,
        'items': sale.items.all(),
        'shop_name': "ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ",
        'shop_address': "જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત",
        'shop_phone': "+91 98765 43210",
    }
    return render(request, 'sales/receipt.html', context)


@cashier_or_admin_required
def sale_list(request):
    """
    Sales & Invoice History Directory.
    Admin sees all sales.
    Cashiers see ONLY their own created sales.
    Supports multi-criteria filtering: search, date range, payment method, payment status, cashier.
    """
    is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin

    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    method_filter = request.GET.get('method', '')
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    cashier_filter = request.GET.get('cashier', '').strip()

    sales_qs = Sale.objects.select_related('customer', 'created_by').all()

    # STRICT BACKEND AUTHORIZATION: Cashier sees ONLY their own sales
    if not is_admin:
        sales_qs = sales_qs.filter(created_by=request.user)
    elif cashier_filter:
        sales_qs = sales_qs.filter(created_by_id=cashier_filter)

    if query:
        sales_qs = sales_qs.filter(
            models.Q(sale_id__icontains=query) |
            models.Q(customer__name__icontains=query) |
            models.Q(customer__mobile__icontains=query)
        )

    if status_filter:
        sales_qs = sales_qs.filter(payment_status=status_filter)

    if method_filter:
        sales_qs = sales_qs.filter(payment_method=method_filter)

    if date_from:
        sales_qs = sales_qs.filter(sale_date__date__gte=date_from)

    if date_to:
        sales_qs = sales_qs.filter(sale_date__date__lte=date_to)

    cashiers_list = []
    if is_admin:
        from django.contrib.auth.models import User
        cashiers_list = User.objects.filter(sales__isnull=False).distinct()

    paginator = Paginator(sales_qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'sales': page_obj.object_list,
        'query': query,
        'status_filter': status_filter,
        'method_filter': method_filter,
        'date_from': date_from,
        'date_to': date_to,
        'cashier_filter': cashier_filter,
        'cashiers_list': cashiers_list,
        'is_admin': is_admin
    }
    return render(request, 'sales/sale_list.html', context)


@cashier_or_admin_required
def sale_detail(request, pk):
    """
    Sale Detail Page.
    Supports lookup by integer primary key or sale_id string (SAL-XXXXXX).
    Admin sees any sale. Cashier sees only their own sales.
    Completed sales are immutable (cannot be edited/deleted).
    """
    if str(pk).isdigit():
        sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product'), pk=pk)
    else:
        sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product'), sale_id__iexact=pk)

    is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin
    if not is_admin and sale.created_by != request.user:
        return HttpResponseForbidden("You are not authorized to view this sale record.")

    context = {
        'sale': sale,
        'items': sale.items.all(),
        'is_admin': is_admin
    }
    return render(request, 'sales/sale_detail.html', context)


@cashier_or_admin_required
def sale_invoice(request, pk):
    """
    Professional A4 Print Invoice View.
    Supports lookup by integer primary key or sale_id string.
    Customer-facing tax invoice document.
    STRICTLY EXCLUDES purchase prices, profit, supplier data.
    """
    if str(pk).isdigit():
        sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product'), pk=pk)
    else:
        sale = get_object_or_404(Sale.objects.select_related('customer', 'created_by').prefetch_related('items__product'), sale_id__iexact=pk)

    is_admin = hasattr(request.user, 'profile') and request.user.profile.is_admin
    if not is_admin and sale.created_by != request.user:
        return HttpResponseForbidden("You are not authorized to view this invoice.")

    context = {
        'sale': sale,
        'items': sale.items.all(),
        'shop_name': "ભાગ્યલક્ષ્મી એન્ટરપ્રાઇઝ",
        'shop_address': "જ્યોતિ હોસ્પિટલની સામે નુતન રોડ, વિસનગર, ગુજરાત",
        'shop_phone': "+91 98765 43210",
        'is_admin': is_admin
    }
    return render(request, 'sales/invoice.html', context)


@cashier_or_admin_required
def sale_edit(request, pk):
    messages.error(request, "This completed sale cannot be edited or deleted.")
    return redirect('sales:detail', pk=pk)


@cashier_or_admin_required
def sale_delete(request, pk):
    messages.error(request, "This completed sale cannot be edited or deleted.")
    return redirect('sales:detail', pk=pk)
