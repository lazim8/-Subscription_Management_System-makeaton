from django.contrib import admin
from .models import Tax, Discount, Subscription, SubscriptionLine, SubscriptionAuditLog


@admin.register(Tax)
class TaxAdmin(admin.ModelAdmin):
    list_display = ('name', 'rate', 'is_default', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_default')
    search_fields = ('name',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'discount_type', 'value', 'target_scope', 'used_count', 'max_uses', 'start_date', 'end_date', 'is_active')
    list_filter = ('discount_type', 'target_scope', 'is_active')
    search_fields = ('code', 'name')


class SubscriptionLineInline(admin.TabularInline):
    model = SubscriptionLine
    extra = 1


class SubscriptionAuditLogInline(admin.TabularInline):
    model = SubscriptionAuditLog
    extra = 0
    readonly_fields = ('from_status', 'to_status', 'changed_by', 'timestamp', 'notes')
    can_delete = False


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('subscription_number', 'customer', 'plan', 'status', 'start_date', 'expiry_date', 'recurring_total', 'created_at')
    list_filter = ('status', 'plan', 'payment_terms')
    search_fields = ('subscription_number', 'customer__email', 'customer__company_name')
    readonly_fields = ('subscription_number', 'created_at', 'updated_at')
    inlines = [SubscriptionLineInline, SubscriptionAuditLogInline]
