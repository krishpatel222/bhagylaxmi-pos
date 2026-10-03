from django import forms
from .models import Customer


class CustomerForm(forms.ModelForm):
    """
    Admin Form: Includes full business and financial fields (opening_balance).
    """
    class Meta:
        model = Customer
        fields = [
            'name', 'mobile', 'whatsapp', 'email',
            'address', 'city', 'state', 'pincode',
            'gst_number', 'opening_balance', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Full Name'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp Number (Optional)'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Delivery / Billing Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (e.g. Visnagar)'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit PIN Code'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '15-digit GSTIN (Optional)', 'style': 'text-transform: uppercase;'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Customer name is required.")
        return name

    def clean_opening_balance(self):
        val = self.cleaned_data.get('opening_balance')
        if val is not None and val < 0:
            raise forms.ValidationError("Opening balance cannot be negative.")
        return val


class CashierCustomerForm(forms.ModelForm):
    """
    Cashier Form: STRICTLY EXCLUDES opening_balance and private financial fields.
    """
    class Meta:
        model = Customer
        fields = [
            'name', 'mobile', 'whatsapp', 'email',
            'address', 'city', 'state', 'pincode',
            'gst_number', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Customer Full Name'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 9876543210'}),
            'whatsapp': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp Number (Optional)'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'customer@email.com'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Delivery / Billing Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City (e.g. Visnagar)'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'State'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '6-digit PIN Code'}),
            'gst_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '15-digit GSTIN (Optional)', 'style': 'text-transform: uppercase;'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notes...'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Customer name is required.")
        return name
