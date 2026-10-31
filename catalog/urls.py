from django.urls import path
from .views import (
    ProductListView,
    ProductCreateView,
    ProductUpdateView,
    ProductVariantCreateView,
    ProductVariantDeleteView,
    PlanListView,
    PlanCreateView,
    PlanUpdateView,
    QuotationTemplateListView,
    QuotationTemplateCreateView,
    QuotationTemplateDetailView,
)

app_name = 'catalog'

urlpatterns = [
    # Products & Variants
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/new/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/edit/', ProductUpdateView.as_view(), name='product-edit'),
    path('products/<int:product_id>/variants/add/', ProductVariantCreateView.as_view(), name='product-variant-add'),
    path('variants/<int:pk>/delete/', ProductVariantDeleteView.as_view(), name='product-variant-delete'),

    # Billing Plans
    path('plans/', PlanListView.as_view(), name='plan-list'),
    path('plans/new/', PlanCreateView.as_view(), name='plan-create'),
    path('plans/<int:pk>/edit/', PlanUpdateView.as_view(), name='plan-edit'),

    # Quotation Templates
    path('templates/', QuotationTemplateListView.as_view(), name='quotation-template-list'),
    path('templates/new/', QuotationTemplateCreateView.as_view(), name='quotation-template-create'),
    path('templates/<int:pk>/', QuotationTemplateDetailView.as_view(), name='quotation-template-detail'),
]
