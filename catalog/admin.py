from django.contrib import admin
from .models import Product, ProductVariant, Plan, QuotationTemplate, QuotationTemplateLine


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'sales_price', 'cost_price', 'is_active', 'created_at')
    list_filter = ('product_type', 'is_active')
    search_fields = ('name', 'notes')
    inlines = [ProductVariantInline]


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'price', 'billing_period', 'min_quantity',
        'available_from', 'auto_close', 'closable', 'pausable', 'renewable', 'is_active'
    )
    list_filter = ('billing_period', 'auto_close', 'closable', 'pausable', 'renewable', 'is_active')
    search_fields = ('name',)


class QuotationTemplateLineInline(admin.TabularInline):
    model = QuotationTemplateLine
    extra = 1


@admin.register(QuotationTemplate)
class QuotationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'plan', 'validity_days', 'created_at')
    search_fields = ('name', 'description')
    inlines = [QuotationTemplateLineInline]
