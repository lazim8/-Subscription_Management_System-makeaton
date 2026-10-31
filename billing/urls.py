from django.urls import path
from django.http import HttpResponse
from .views import (
    SubscriptionListView,
    SubscriptionDetailView,
    SubscriptionCreateView,
    SubscriptionTransitionView,
    DiscountTaxListView,
    TaxCreateView,
    TaxUpdateView,
    DiscountCreateView,
    DiscountUpdateView,
)

app_name = 'billing'

def placeholder_future(request):
    return HttpResponse("Module coming in next steps")

placeholder_billing = placeholder_future

urlpatterns = [
    # Subscriptions & Quotation Conversion
    path('subscriptions/', SubscriptionListView.as_view(), name='subscription-list'),
    path('subscriptions/new/', SubscriptionCreateView.as_view(), name='subscription-create'),
    path('subscriptions/<int:pk>/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path('subscriptions/<int:pk>/transition/', SubscriptionTransitionView.as_view(), name='subscription-transition'),

    # Taxes & Discounts (Admin Only)
    path('discounts-taxes/', DiscountTaxListView.as_view(), name='discount-tax-list'),
    path('taxes/new/', TaxCreateView.as_view(), name='tax-create'),
    path('taxes/<int:pk>/edit/', TaxUpdateView.as_view(), name='tax-edit'),
    path('discounts/new/', DiscountCreateView.as_view(), name='discount-create'),
    path('discounts/<int:pk>/edit/', DiscountUpdateView.as_view(), name='discount-edit'),

    # Stubs for Invoices, Payments, Reports, and Portal (coming in Step 4 & 5)
    path('invoices/', placeholder_future, name='invoice-list'),
    path('payments/', placeholder_future, name='payment-list'),
    path('reports/', placeholder_future, name='reports'),
    path('portal/subscriptions/', placeholder_future, name='customer-portal-subscriptions'),
    path('portal/invoices/', placeholder_future, name='customer-portal-invoices'),
]
