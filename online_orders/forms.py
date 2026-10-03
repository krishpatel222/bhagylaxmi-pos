from decimal import Decimal
from django import forms
from django.core.validators import RegexValidator
from .models import OnlineOrder


mobile_validator = RegexValidator(
    regex=r'^(?:\+91|0)?[6-9]\d{9}$',
    message="Enter a valid 10-digit Indian mobile number."
)

pincode_validator = RegexValidator(
    regex=r'^[1-9][0-9]{5}$',
    message="Enter a valid 6-digit Indian PIN code."
)


class OnlineOrderForm(forms.ModelForm):
    mobile = forms.CharField(max_length=15, validators=[mobile_validator], widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '10-digit Mobile Number'}))
    pincode = forms.CharField(max_length=10, validators=[pincode_validator], widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit PIN Code'}))

    class Meta:
        model = OnlineOrder
        fields = [
            'customer', 'customer_name', 'mobile', 'whatsapp', 'email',
            'full_address', 'city', 'state', 'pincode',
            'order_amount', 'payment_received', 'payment_status',
            'courier_name', 'tracking_number', 'status', 'notes'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select', 'id': 'custSelect'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Full Name'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp Number (Optional)'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
            'full_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Complete Delivery Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (e.g. Visnagar)'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'order_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_received': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'courier_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. India Post, Delhivery, DTDC'}),
            'tracking_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tracking AWB Number'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Internal notes...'}),
        }

    def clean_order_amount(self):
        amt = self.cleaned_data.get('order_amount')
        if amt is None or amt < Decimal('0.00'):
            raise forms.ValidationError("Order amount cannot be negative.")
        return amt

    def clean_payment_received(self):
        received = self.cleaned_data.get('payment_received')
        if received is None or received < Decimal('0.00'):
            raise forms.ValidationError("Payment received cannot be negative.")
        return received

    def clean(self):
        cleaned_data = super().clean()
        order_amt = cleaned_data.get('order_amount') or Decimal('0.00')
        pay_received = cleaned_data.get('payment_received') or Decimal('0.00')

        if pay_received > order_amt:
            raise forms.ValidationError("Payment received cannot exceed total order amount.")

        # Server-side calculation of pending amount
        cleaned_data['pending_amount'] = order_amt - pay_received
        return cleaned_data
