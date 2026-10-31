"""
Brightloop Catalog Models.
Handles Products, Product Variants (e.g. Brand / Odoo +$560),
Billing Plans (Daily, Weekly, Monthly, Yearly with lifecycle flags),
and Quotation Templates with line items.
"""
from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal


class Product(models.Model):
    """
    Core software, add-on, service, or hardware sold by Brightloop.
    """
    class ProductType(models.TextChoices):
        SOFTWARE = 'software', 'Software'
        ADDON = 'addon', 'Add-on'
        SERVICE = 'service', 'Professional Service'
        HARDWARE = 'hardware', 'Hardware'

    name = models.CharField(max_length=255, unique=True, help_text="Product title (e.g. Brightloop CRM)")
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.SOFTWARE,
        help_text="Type of product offered"
    )
    sales_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Base selling price"
    )
    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Internal cost to deliver"
    )
    notes = models.TextField(blank=True, help_text="Internal notes or product description")
    is_active = models.BooleanField(default=True, help_text="Active products are available in quotes and plans")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (${self.sales_price})"

    @property
    def has_variants(self):
        return self.variants.filter(is_active=True).exists()


class ProductVariant(models.Model):
    """
    Product variant adjustments (e.g. choosing the Odoo brand adds +$560 to the price).
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    attribute = models.CharField(max_length=100, default='Brand', help_text="Variant dimension (e.g. Brand, Edition)")
    value = models.CharField(max_length=100, help_text="Variant value (e.g. Odoo, Enterprise)")
    extra_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Additional price adjustment added to base product price"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('product', 'attribute', 'value')
        ordering = ['attribute', 'value']

    def __str__(self):
        sign = "+" if self.extra_price >= 0 else ""
        return f"{self.product.name} - {self.attribute}: {self.value} ({sign}${self.extra_price})"

    @property
    def total_unit_price(self):
        """Calculates total unit price including variant adjustment."""
        return self.product.sales_price + self.extra_price


class Plan(models.Model):
    """
    Subscription billing cadence, pricing, and lifecycle policies.
    """
    class BillingPeriod(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
        YEARLY = 'yearly', 'Yearly'

    name = models.CharField(max_length=255, unique=True, help_text="Plan name (e.g. Startup Monthly, Enterprise Annual)")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Recurring subscription fee"
    )
    billing_period = models.CharField(
        max_length=20,
        choices=BillingPeriod.choices,
        default=BillingPeriod.MONTHLY,
        help_text="Cadence of recurring billing run"
    )
    min_quantity = models.PositiveIntegerField(default=1, help_text="Minimum seats or licenses required")
    available_from = models.DateField(help_text="Date when this plan becomes available for signup/quotation")
    available_to = models.DateField(null=True, blank=True, help_text="Optional end date when plan stops being offered")

    # Lifecycle & Closure Flags (Admin decides plan by plan)
    auto_close = models.BooleanField(default=False, help_text="Automatically closes subscription on end date")
    closable = models.BooleanField(default=True, help_text="Allows early closure before term ends")
    pausable = models.BooleanField(default=True, help_text="Allows customer/staff to pause billing")
    renewable = models.BooleanField(default=True, help_text="Allows renewing after expiration")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (${self.price}/{self.get_billing_period_display()})"


class QuotationTemplate(models.Model):
    """
    Preset quotation blueprints used by sales reps so they don't build offers from scratch.
    """
    name = models.CharField(max_length=255, unique=True, help_text="Template title (e.g. Standard SaaS Solution)")
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='quotation_templates')
    validity_days = models.PositiveIntegerField(default=30, help_text="Number of days the quote remains valid")
    description = models.TextField(blank=True, help_text="Notes explaining this offer package")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.validity_days} days validity)"


class QuotationTemplateLine(models.Model):
    """
    Line items bundled inside a Quotation Template.
    """
    template = models.ForeignKey(QuotationTemplate, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Locked unit price for this template line")

    def __str__(self):
        return f"{self.quantity}x {self.product.name} @ ${self.unit_price}"

    def save(self, *args, **kwargs):
        # Automatically default unit_price if not explicitly provided
        if self.unit_price is None:
            if self.variant:
                self.unit_price = self.variant.total_unit_price
            else:
                self.unit_price = self.product.sales_price
        super().save(*args, **kwargs)
