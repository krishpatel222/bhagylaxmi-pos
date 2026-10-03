from django import forms
from .models import Product
from categories.models import Category, Brand


class ProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Category / કેટેગરી પસંદ કરો"
    )
    brand = forms.ModelChoiceField(
        queryset=Brand.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label="Select Brand (Optional) / બ્રાન્ડ (વૈકલ્પિક)"
    )

    class Meta:
        model = Product
        fields = [
            'name', 'gujarati_name', 'sku', 'barcode',
            'category', 'brand', 'purchase_price', 'selling_price',
            'mrp', 'gst_rate', 'opening_stock', 'current_stock',
            'minimum_stock', 'unit', 'image', 'description', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Krishna Mukut'}),
            'gujarati_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. કૃષ્ણ મુગટ'}),
            'sku': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. KRMUK-001'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Scan or type barcode'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'mrp': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'gst_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
            'opening_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'current_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'minimum_stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError("Product name is required.")
        return name

    def clean_sku(self):
        sku = self.cleaned_data.get('sku', '').strip()
        if sku:
            qs = Product.objects.filter(sku__iexact=sku)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"SKU '{sku}' is already assigned to another product.")
        return sku or None

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode', '').strip()
        if barcode:
            qs = Product.objects.filter(barcode__iexact=barcode)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(f"Barcode '{barcode}' is already assigned to another product.")
        return barcode or None

    def clean_purchase_price(self):
        val = self.cleaned_data.get('purchase_price')
        if val is not None and val < 0:
            raise forms.ValidationError("Purchase price cannot be negative.")
        return val

    def clean_selling_price(self):
        val = self.cleaned_data.get('selling_price')
        if val is not None and val < 0:
            raise forms.ValidationError("Selling price cannot be negative.")
        return val

    def clean_mrp(self):
        val = self.cleaned_data.get('mrp')
        if val is not None and val < 0:
            raise forms.ValidationError("MRP cannot be negative.")
        return val

    def clean_gst_rate(self):
        val = self.cleaned_data.get('gst_rate')
        if val is not None and (val < 0 or val > 100):
            raise forms.ValidationError("GST rate must be between 0% and 100%.")
        return val

    def clean_opening_stock(self):
        val = self.cleaned_data.get('opening_stock')
        if val is not None and val < 0:
            raise forms.ValidationError("Opening stock cannot be negative.")
        return val

    def clean_minimum_stock(self):
        val = self.cleaned_data.get('minimum_stock')
        if val is not None and val < 0:
            raise forms.ValidationError("Minimum stock cannot be negative.")
        return val
