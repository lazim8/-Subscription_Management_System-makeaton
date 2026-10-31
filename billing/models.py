"""
Brightloop Billing Models:
- Taxes & Admin Discount Rules (Fixed/Percentage, Minimums, Validity Dates, Usage Limits)
- Subscriptions with unique auto-generated number (SUB-2026-0001)
- Strict State Machine: Draft -> Quotation -> Confirmed -> Active -> Closed (with Paused & Renewal)
- Subscription Lines with Product, Variant, Quantity, Unit Price, Taxes, and Totals
- Audit Log tracking every state transition with timestamp and user
"""
from decimal import Decimal
from datetime import date, timedelta
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator
from django.conf import settings
from catalog.models import Product, ProductVariant, Plan


class Tax(models.Model):
    """
    Tax rules configured by Administrator (e.g. VAT 10%, Sales Tax 8.25%, Zero Tax 0%).
    """
    name = models.CharField(max_length=100, unique=True, help_text="Tax name (e.g. Standard VAT)")
    rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax percentage (e.g. 10.00 for 10%)"
    )
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Automatically selected on new lines")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Taxes'

    def __str__(self):
        return f"{self.name} ({self.rate}%)"

    def calculate_tax(self, amount):
        """Calculates tax dollar amount on given line subtotal."""
        if not amount:
            return Decimal('0.00')
        return (Decimal(str(amount)) * (self.rate / Decimal('100.00'))).quantize(Decimal('0.01'))

    def save(self, *args, **kwargs):
        # If this tax is set as default, unset any existing default
        if self.is_default:
            Tax.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Discount(models.Model):
    """
    Admin-only discount rules:
    - Fixed dollar amount or percentage
    - Optional spend threshold (min_purchase) or seat threshold (min_quantity)
    - Auto-expiring start and end dates
    - Max usage limits with live used_count tracking
    - Scope: whole subscription or specific product
    """
    class DiscountType(models.TextChoices):
        PERCENT = 'percent', 'Percentage (%)'
        FIXED = 'fixed', 'Fixed Dollar Amount ($)'

    class TargetScope(models.TextChoices):
        SUBSCRIPTION = 'subscription', 'Whole Subscription'
        PRODUCT = 'product', 'Specific Product'

    code = models.CharField(max_length=50, unique=True, help_text="Promo code in uppercase (e.g. WELCOME20)")
    name = models.CharField(max_length=255, help_text="Campaign name or discount purpose")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENT)
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Percentage value (e.g. 15 for 15%) or dollar amount (e.g. 50 for $50 off)"
    )
    target_scope = models.CharField(max_length=20, choices=TargetScope.choices, default=TargetScope.SUBSCRIPTION)
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, help_text="Required if scope is Specific Product")

    min_purchase = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Minimum spend required to qualify for discount"
    )
    min_quantity = models.PositiveIntegerField(default=0, help_text="Minimum seat quantity required")

    start_date = models.DateField(default=timezone.now, help_text="Date when promo begins")
    end_date = models.DateField(null=True, blank=True, help_text="Date when promo automatically expires")

    max_uses = models.PositiveIntegerField(null=True, blank=True, help_text="Total usage limit (e.g. first 50 customers)")
    used_count = models.PositiveIntegerField(default=0, help_text="Times this discount has been applied")

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        val = f"{self.value}%" if self.discount_type == self.DiscountType.PERCENT else f"${self.value}"
        return f"{self.code} ({val} off) - {self.name}"

    def is_valid_for(self, subtotal=Decimal('0.00'), quantity=1):
        """Checks if the discount is active, unexpired, and meets qualification thresholds."""
        if not self.is_active:
            return False, "Discount is inactive."

        today = date.today()
        if self.start_date > today:
            return False, f"Discount becomes active on {self.start_date}."
        if self.end_date and self.end_date < today:
            return False, f"Discount expired on {self.end_date}."

        if self.max_uses and self.used_count >= self.max_uses:
            return False, "Discount usage limit has been reached."

        if subtotal < self.min_purchase:
            return False, f"Requires a minimum purchase of ${self.min_purchase}."

        if quantity < self.min_quantity:
            return False, f"Requires a minimum quantity of {self.min_quantity} seats."

        return True, "Valid"

    def calculate_discount(self, subtotal):
        """Calculates discount amount against a subtotal."""
        subtotal = Decimal(str(subtotal))
        if self.discount_type == self.DiscountType.PERCENT:
            amount = (subtotal * (self.value / Decimal('100.00'))).quantize(Decimal('0.01'))
            return min(amount, subtotal)
        else:
            return min(self.value, subtotal)


class Subscription(models.Model):
    """
    Central subscription entity with auto-generated unique number and state machine:
    Draft -> Quotation -> Confirmed -> Active -> Closed (with Paused & Renewal support)
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        QUOTATION = 'quotation', 'Quotation'
        CONFIRMED = 'confirmed', 'Confirmed'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        CLOSED = 'closed', 'Closed'

    class PaymentTerms(models.TextChoices):
        IMMEDIATE = 'immediate', 'Due on Receipt'
        NET_15 = 'net_15', 'Net 15 Days'
        NET_30 = 'net_30', 'Net 30 Days'
        NET_60 = 'net_60', 'Net 60 Days'

    subscription_number = models.CharField(max_length=64, unique=True, editable=False, db_index=True)
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    discount = models.ForeignKey(Discount, on_delete=models.SET_NULL, null=True, blank=True, related_name='subscriptions')

    payment_terms = models.CharField(max_length=20, choices=PaymentTerms.choices, default=PaymentTerms.IMMEDIATE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)

    start_date = models.DateField(default=date.today)
    expiry_date = models.DateField(help_text="Scheduled expiration or renewal review date")
    next_billing_date = models.DateField(default=date.today, help_text="Date when next automated billing invoice is due")

    notes = models.TextField(blank=True, help_text="Internal notes or contract terms")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_subscriptions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subscription_number} - {self.customer.company_name or self.customer.email} ({self.get_status_display()})"

    def save(self, *args, **kwargs):
        # Generate auto-incrementing subscription number (e.g. SUB-2026-0001) if not present
        if not self.subscription_number:
            year = date.today().year
            last_sub = Subscription.objects.filter(subscription_number__startswith=f"SUB-{year}-").order_by('-id').first()
            if last_sub:
                try:
                    last_num = int(last_sub.subscription_number.split('-')[-1])
                    new_num = last_num + 1
                except ValueError:
                    new_num = Subscription.objects.count() + 1
            else:
                new_num = Subscription.objects.count() + 1
            self.subscription_number = f"SUB-{year}-{new_num:04d}"

        # If expiry date not set, default to 1 year from start_date
        if not self.expiry_date:
            self.expiry_date = self.start_date + timedelta(days=365)

        super().save(*args, **kwargs)

    # --- Financial & Quantity Calculations ---

    @property
    def total_quantity(self):
        return sum(line.quantity for line in self.lines.all())

    @property
    def subtotal(self):
        return sum(line.line_subtotal for line in self.lines.all())

    @property
    def tax_total(self):
        return sum(line.line_tax for line in self.lines.all())

    @property
    def discount_amount(self):
        if self.discount:
            valid, _ = self.discount.is_valid_for(self.subtotal, self.total_quantity)
            if valid:
                return self.discount.calculate_discount(self.subtotal)
        return Decimal('0.00')

    @property
    def recurring_total(self):
        """Total invoice amount per recurring billing period."""
        return (self.subtotal - self.discount_amount + self.tax_total).quantize(Decimal('0.01'))

    @property
    def normalized_mrr(self):
        """Normalized Monthly Recurring Revenue based on plan cadence."""
        total = self.recurring_total
        period = self.plan.billing_period
        if period == Plan.BillingPeriod.DAILY:
            return (total * Decimal('30.00')).quantize(Decimal('0.01'))
        elif period == Plan.BillingPeriod.WEEKLY:
            return (total * Decimal('4.33')).quantize(Decimal('0.01'))
        elif period == Plan.BillingPeriod.MONTHLY:
            return total.quantize(Decimal('0.01'))
        elif period == Plan.BillingPeriod.YEARLY:
            return (total / Decimal('12.00')).quantize(Decimal('0.01'))
        return total

    # --- State Machine Validation & Transitions ---

    VALID_TRANSITIONS = {
        Status.DRAFT: [Status.QUOTATION, Status.CLOSED],
        Status.QUOTATION: [Status.CONFIRMED, Status.DRAFT, Status.CLOSED],
        Status.CONFIRMED: [Status.ACTIVE, Status.CLOSED],
        Status.ACTIVE: [Status.PAUSED, Status.CLOSED],
        Status.PAUSED: [Status.ACTIVE, Status.CLOSED],
        Status.CLOSED: [Status.ACTIVE],  # Renewal
    }

    def can_transition_to(self, new_status):
        """Validates state transition against workflow rules and plan policies."""
        if new_status == self.status:
            return True, "No change"

        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            return False, f"Cannot transition from {self.get_status_display()} to {dict(self.Status.choices).get(new_status)}."

        # Check plan lifecycle flags
        if new_status == self.Status.PAUSED and not self.plan.pausable:
            return False, f"Plan '{self.plan.name}' does not allow pausing."

        if new_status == self.Status.CLOSED and self.status == self.Status.ACTIVE and not self.plan.closable:
            # If not closable early, can only close if expired
            if date.today() < self.expiry_date:
                return False, f"Plan '{self.plan.name}' does not allow early closure before {self.expiry_date}."

        if self.status == self.Status.CLOSED and new_status == self.Status.ACTIVE and not self.plan.renewable:
            return False, f"Plan '{self.plan.name}' does not permit renewal."

        return True, "Valid transition"

    def transition_to(self, new_status, user=None, notes=""):
        """Executes state transition, writes audit log, and handles discounts."""
        allowed, msg = self.can_transition_to(new_status)
        if not allowed:
            raise ValueError(msg)

        old_status = self.status
        self.status = new_status

        # If activating for the first time with a discount, increment used_count
        if new_status == self.Status.ACTIVE and old_status != self.Status.PAUSED and self.discount:
            self.discount.used_count += 1
            self.discount.save(update_fields=['used_count'])

        self.save()

        # Record in Audit Log
        SubscriptionAuditLog.objects.create(
            subscription=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            notes=notes or f"Transitioned from {old_status} to {new_status}"
        )


class SubscriptionLine(models.Model):
    """
    Line items attached to a Subscription (Product, Variant, Qty, Unit Price, Tax).
    """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    tax = models.ForeignKey(Tax, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        v = f" ({self.variant.value})" if self.variant else ""
        return f"{self.quantity}x {self.product.name}{v} @ ${self.unit_price}"

    @property
    def line_subtotal(self):
        return (Decimal(str(self.quantity)) * Decimal(str(self.unit_price))).quantize(Decimal('0.01'))

    @property
    def line_tax(self):
        if self.tax:
            return self.tax.calculate_tax(self.line_subtotal)
        return Decimal('0.00')

    @property
    def line_total(self):
        return self.line_subtotal + self.line_tax


class SubscriptionAuditLog(models.Model):
    """
    Immutable audit log recording who changed subscription state and when.
    """
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE, related_name='audit_logs')
    from_status = models.CharField(max_length=20)
    to_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        by = self.changed_by.email if self.changed_by else "System"
        return f"{self.subscription.subscription_number}: {self.from_status} -> {self.to_status} by {by} at {self.timestamp}"
