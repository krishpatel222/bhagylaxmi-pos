from django import forms
from .models import ShopSettings


class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = ShopSettings
        fields = [
            'shop_name', 'address', 'city', 'state', 'pincode',
            'mobile', 'whatsapp', 'email', 'gst_number', 'logo',
            'invoice_prefix', 'order_prefix', 'currency', 'default_gst_rate'
        ]
        widgets = {
            'shop_name': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'order_prefix': forms.TextInput(attrs={'class': 'form-control'}),
            'currency': forms.TextInput(attrs={'class': 'form-control'}),
            'default_gst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
