from django import forms
from .models import Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 'company_name', 'mobile', 'whatsapp', 'email',
            'address', 'city', 'state', 'pincode', 'gst_number',
            'opening_balance', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier Person Name'}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Business / Firm Name'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp Number (Optional)'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@domain.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Shop / Warehouse Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (e.g. Visnagar, Ahmedabad)'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit PIN Code'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '15-digit GSTIN (Optional)', 'style': 'text-transform: uppercase;'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes or terms...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Supplier name is required.")
        return name

    def clean_opening_balance(self):
        val = self.cleaned_data.get('opening_balance')
        if val is not None and val < 0:
            raise forms.ValidationError("Opening balance cannot be negative.")
        return val

    def clean_gst_number(self):
        gst = self.cleaned_data.get('gst_number', '').strip().upper()
        return gst or None

    def clean_pincode(self):
        pin = self.cleaned_data.get('pincode', '').strip()
        return pin or None
