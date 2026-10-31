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
    AutomatedBillingRunView,
    InvoiceListView,
    InvoiceDetailView,
    InvoiceStatusUpdateView,
    InvoicePaymentRecordView,
    PaymentListView,
    OverdueInvoicesListView,
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

    # Invoices & Automated Billing Engine
    path('invoices/', InvoiceListView.as_view(), name='invoice-list'),
    path('invoices/billing-run/', AutomatedBillingRunView.as_view(), name='automated-billing-run'),
    path('invoices/overdue/', OverdueInvoicesListView.as_view(), name='overdue-list'),
    path('invoices/<int:pk>/', InvoiceDetailView.as_view(), name='invoice-detail'),
    path('invoices/<int:pk>/status/', InvoiceStatusUpdateView.as_view(), name='invoice-status-update'),
    path('invoices/<int:pk>/pay/', InvoicePaymentRecordView.as_view(), name='invoice-payment-record'),

    # Payments Ledger
    path('payments/', PaymentListView.as_view(), name='payment-list'),

    # Stubs for Reports and Customer Portal (Step 5)
    path('reports/', placeholder_future, name='reports'),
    path('portal/subscriptions/', placeholder_future, name='customer-portal-subscriptions'),
    path('portal/invoices/', placeholder_future, name='customer-portal-invoices'),
]
