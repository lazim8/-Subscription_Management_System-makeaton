from django import forms
from .models import Product, ProductVariant, Plan, QuotationTemplate, QuotationTemplateLine


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'product_type', 'sales_price', 'cost_price', 'notes', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Brightloop CRM Core'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'sales_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Technical details or licensing notes'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ['attribute', 'value', 'extra_price', 'is_active']
        widgets = {
            'attribute': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Brand'}),
            'value': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Odoo'}),
            'extra_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '560.00'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = [
            'name', 'price', 'billing_period', 'min_quantity',
            'available_from', 'available_to',
            'auto_close', 'closable', 'pausable', 'renewable', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Enterprise Annual'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '990.00'}),
            'billing_period': forms.Select(attrs={'class': 'form-select'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'available_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'available_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'auto_close': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'closable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pausable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'renewable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class QuotationTemplateForm(forms.ModelForm):
    class Meta:
        model = QuotationTemplate
        fields = ['name', 'plan', 'validity_days', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Enterprise Standard Quote'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'validity_days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Package highlights'}),
        }
