from django import forms
from products.models import Product
from .models import InventoryTransaction


class StockAdjustmentForm(forms.Form):
    ADJUSTMENT_CHOICES = [
        (InventoryTransaction.TYPE_ADJUSTMENT_IN, 'Adjustment In (Add Stock)'),
        (InventoryTransaction.TYPE_ADJUSTMENT_OUT, 'Adjustment Out (Remove Stock)'),
        (InventoryTransaction.TYPE_DAMAGE, 'Record Damage (Remove Stock)'),
    ]

    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Product / પ્રોડક્ટ પસંદ કરો"
    )
    transaction_type = forms.ChoiceField(
        choices=ADJUSTMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quantity = forms.DecimalField(
        max_digits=12, decimal_places=2, min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Quantity'})
    )
    note = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Reason or reference note for this stock adjustment...'})
    )
