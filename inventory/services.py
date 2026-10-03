from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from products.models import Product
from .models import InventoryTransaction


@transaction.atomic
def change_stock(product, quantity, transaction_type, user=None, reference_type=None, reference_id=None, note="", allow_negative=False):
    """
    Atomic, thread-safe stock modification service.
    
    Parameters:
    - product: Product instance or product primary key ID
    - quantity: Decimal or numeric amount to add/remove
    - transaction_type: Choice from InventoryTransaction.TRANSACTION_TYPE_CHOICES
    - user: User instance performing the change
    - reference_type: Optional string tag ('PURCHASE', 'SALE', 'ADJUSTMENT', etc.)
    - reference_id: Optional string/ID reference
    - note: Description or reason for stock movement
    - allow_negative: Boolean flag to allow negative stock (Default: False)
    
    Returns:
    - InventoryTransaction instance created
    """
    qty = Decimal(str(quantity))
    if qty <= 0:
        raise ValueError("Stock transaction quantity must be greater than zero.")

    # Lock Product row to prevent race conditions during concurrent POS sales
    if isinstance(product, (int, str)):
        product_obj = Product.objects.select_for_update().get(pk=product)
    else:
        product_obj = Product.objects.select_for_update().get(pk=product.pk)

    prev_stock = Decimal(str(product_obj.current_stock or 0))

    # Determine direction of stock movement
    increasing_types = [
        InventoryTransaction.TYPE_PURCHASE_IN,
        InventoryTransaction.TYPE_SALES_RETURN,
        InventoryTransaction.TYPE_ADJUSTMENT_IN,
        InventoryTransaction.TYPE_OPENING_STOCK,
    ]

    decreasing_types = [
        InventoryTransaction.TYPE_SALE_OUT,
        InventoryTransaction.TYPE_PURCHASE_RETURN,
        InventoryTransaction.TYPE_ADJUSTMENT_OUT,
        InventoryTransaction.TYPE_DAMAGE,
    ]

    if transaction_type in increasing_types:
        new_stock = prev_stock + qty
    elif transaction_type in decreasing_types:
        new_stock = prev_stock - qty
    else:
        raise ValueError(f"Invalid transaction type: {transaction_type}")

    # Check negative stock restriction
    if new_stock < 0 and not allow_negative:
        raise ValidationError(f"Insufficient stock for '{product_obj.name}'. Current stock: {prev_stock} {product_obj.unit}, Attempted removal: {qty} {product_obj.unit}.")

    # Update Product stock
    product_obj.current_stock = new_stock
    product_obj.save(update_fields=['current_stock', 'updated_at'])

    # Create immutable audit log record
    tx_record = InventoryTransaction.objects.create(
        product=product_obj,
        transaction_type=transaction_type,
        quantity=qty,
        previous_stock=prev_stock,
        new_stock=new_stock,
        reference_type=reference_type,
        reference_id=reference_id,
        note=note,
        created_by=user
    )

    return tx_record
