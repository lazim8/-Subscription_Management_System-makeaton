from django import forms
from django.contrib.auth import get_user_model
from .models import Tax, Discount, Subscription, SubscriptionLine

User = get_user_model()


class TaxForm(forms.ModelForm):
    class Meta:
        model = Tax
        fields = ['name', 'rate', 'is_default', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Standard VAT'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '10.00'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class DiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = [
            'code', 'name', 'discount_type', 'value', 'target_scope', 'product',
            'min_purchase', 'min_quantity', 'start_date', 'end_date', 'max_uses', 'is_active'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. WELCOME20'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. New Customer Welcome Discount'}),
            'discount_type': forms.Select(attrs={'class': 'form-select'}),
            'value': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '20.00'}),
            'target_scope': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'min_purchase': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'min_quantity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'placeholder': '0'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'max_uses': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'placeholder': 'Leave empty for unlimited'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()


class SubscriptionForm(forms.ModelForm):
    class Meta:
        model = Subscription
        fields = ['customer', 'plan', 'discount', 'payment_terms', 'start_date', 'expiry_date', 'notes']
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'plan': forms.Select(attrs={'class': 'form-select'}),
            'discount': forms.Select(attrs={'class': 'form-select'}),
            'payment_terms': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Contract specifics or SLA agreements'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limit customer choices to accounts with role='customer'
        self.fields['customer'].queryset = User.objects.filter(role=User.Role.CUSTOMER).order_by('email')
        self.fields['discount'].queryset = Discount.objects.filter(is_active=True).order_by('code')
