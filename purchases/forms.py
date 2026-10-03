from django import forms
from suppliers.models import Supplier
from .models import Purchase


class PurchaseForm(forms.ModelForm):
    supplier = forms.ModelChoiceField(
        queryset=Supplier.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select select2'}),
        empty_label="Select Supplier / સપ્લાયર પસંદ કરો"
    )

    class Meta:
        model = Purchase
        fields = ['supplier', 'invoice_number', 'purchase_date', 'paid_amount', 'notes']
        widgets = {
            'invoice_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. INV-2026-891'}),
            'purchase_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'paid_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional purchase notes...'}),
        }

    def clean_invoice_number(self):
        inv = self.cleaned_data.get('invoice_number', '').strip()
        if not inv:
            raise forms.ValidationError("Supplier invoice number is required.")
        return inv

    def clean_paid_amount(self):
        paid = self.cleaned_data.get('paid_amount')
        if paid is not None and paid < 0:
            raise forms.ValidationError("Paid amount cannot be negative.")
        return paid
