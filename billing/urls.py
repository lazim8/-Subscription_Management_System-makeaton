from django.urls import path
from django.http import HttpResponse

app_name = 'billing'

def placeholder_billing(request):
    return HttpResponse("Billing - Coming in next steps")

urlpatterns = [
    path('subscriptions/', placeholder_billing, name='subscription-list'),
    path('invoices/', placeholder_billing, name='invoice-list'),
    path('payments/', placeholder_billing, name='payment-list'),
    path('discounts-taxes/', placeholder_billing, name='discount-tax-list'),
    path('reports/', placeholder_billing, name='reports'),
    path('portal/subscriptions/', placeholder_billing, name='customer-portal-subscriptions'),
    path('portal/invoices/', placeholder_billing, name='customer-portal-invoices'),
]
