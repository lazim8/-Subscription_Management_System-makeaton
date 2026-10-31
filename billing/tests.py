from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase
from accounts.models import User
from catalog.models import Product, ProductVariant, Plan
from billing.models import Tax, Discount, Subscription, SubscriptionLine, Invoice, Payment


class BillingSystemTestCase(TestCase):
    def setUp(self):
        # Users
        self.admin = User.objects.create_superuser(
            email="admin@test.com",
            password="BrightAdmin123!",
            role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user(
            email="customer@test.com",
            password="AcmeCustomer123!",
            company_name="Acme Inc",
            role=User.Role.CUSTOMER
        )
        self.other_customer = User.objects.create_user(
            email="other@test.com",
            password="OtherCustomer123!",
            company_name="Other Corp",
            role=User.Role.CUSTOMER
        )

        # Products & Variants
        self.product = Product.objects.create(
            name="Test CRM",
            sales_price=Decimal('100.00'),
            cost_price=Decimal('30.00')
        )
        self.variant_odoo = ProductVariant.objects.create(
            product=self.product,
            attribute="Brand",
            value="Odoo",
            extra_price=Decimal('50.00')
        )

        # Plans
        self.plan_monthly = Plan.objects.create(
            name="Monthly Plan",
            price=Decimal('100.00'),
            billing_period=Plan.BillingPeriod.MONTHLY,
            available_from=date(2026, 1, 1),
            pausable=True,
            closable=True,
            renewable=True
        )
        self.plan_locked = Plan.objects.create(
            name="Locked Plan",
            price=Decimal('200.00'),
            billing_period=Plan.BillingPeriod.MONTHLY,
            available_from=date(2026, 1, 1),
            pausable=False,
            closable=False,
            renewable=False
        )

        # Tax & Discount
        self.tax = Tax.objects.create(name="VAT 10%", rate=Decimal('10.00'), is_default=True)
        self.discount_20 = Discount.objects.create(
            code="TEST20",
            name="20% Off",
            discount_type=Discount.DiscountType.PERCENT,
            value=Decimal('20.00'),
            start_date=date(2026, 1, 1)
        )

    def test_product_variant_total_price(self):
        """Test variant extra price calculation (e.g. Odoo +50)."""
        self.assertEqual(self.variant_odoo.total_unit_price, Decimal('150.00'))

    def test_state_machine_valid_flow(self):
        """Test valid state transition Draft -> Quotation -> Confirmed -> Active -> Paused -> Active."""
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan_monthly,
            start_date=date.today(),
            expiry_date=date.today() + timedelta(days=365)
        )
        self.assertEqual(sub.status, Subscription.Status.DRAFT)

        # Draft -> Quotation
        sub.transition_to(Subscription.Status.QUOTATION, user=self.admin)
        self.assertEqual(sub.status, Subscription.Status.QUOTATION)

        # Quotation -> Confirmed
        sub.transition_to(Subscription.Status.CONFIRMED, user=self.admin)
        self.assertEqual(sub.status, Subscription.Status.CONFIRMED)

        # Confirmed -> Active
        sub.transition_to(Subscription.Status.ACTIVE, user=self.admin)
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)

        # Active -> Paused (allowed by plan)
        sub.transition_to(Subscription.Status.PAUSED, user=self.admin)
        self.assertEqual(sub.status, Subscription.Status.PAUSED)

        # Paused -> Active
        sub.transition_to(Subscription.Status.ACTIVE, user=self.admin)
        self.assertEqual(sub.status, Subscription.Status.ACTIVE)

    def test_state_machine_plan_enforcement(self):
        """Test plan lifecycle rules block disallowed transitions (e.g. pause when plan.pausable=False)."""
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan_locked,
            status=Subscription.Status.ACTIVE,
            start_date=date.today(),
            expiry_date=date.today() + timedelta(days=365)
        )
        # Attempting to pause a locked plan must raise ValueError
        with self.assertRaises(ValueError):
            sub.transition_to(Subscription.Status.PAUSED, user=self.admin)

    def test_double_billing_guard(self):
        """Test that automated billing run never generates duplicate invoices for the same cycle."""
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan_monthly,
            status=Subscription.Status.ACTIVE,
            start_date=date.today() - timedelta(days=35),
            next_billing_date=date.today() - timedelta(days=5)
        )
        SubscriptionLine.objects.create(
            subscription=sub,
            product=self.product,
            quantity=2,
            unit_price=self.product.sales_price,
            tax=self.tax
        )

        # First billing run: creates invoice
        self.client.force_login(self.admin)
        response = self.client.post('/billing/invoices/billing-run/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Invoice.objects.filter(subscription=sub).count(), 1)

        # Second billing run immediately after: must NOT create a duplicate
        response2 = self.client.post('/billing/invoices/billing-run/')
        self.assertEqual(response2.status_code, 302)
        self.assertEqual(Invoice.objects.filter(subscription=sub).count(), 1)

    def test_payment_and_auto_settlement(self):
        """Test partial payments and auto-settlement to Paid status."""
        sub = Subscription.objects.create(
            customer=self.customer,
            plan=self.plan_monthly,
            status=Subscription.Status.ACTIVE,
            start_date=date.today()
        )
        inv = Invoice.objects.create(
            subscription=sub,
            customer=self.customer,
            billing_period_start=date.today(),
            billing_period_end=date.today() + timedelta(days=30),
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=15),
            status=Invoice.Status.CONFIRMED,
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('0.00')
        )

        # Partial payment $40
        Payment.objects.create(
            invoice=inv,
            amount=Decimal('40.00'),
            payment_method=Payment.PaymentMethod.CREDIT_CARD
        )
        inv.refresh_from_db()
        self.assertEqual(inv.paid_amount, Decimal('40.00'))
        self.assertEqual(inv.balance_due, Decimal('60.00'))
        self.assertEqual(inv.status, Invoice.Status.CONFIRMED)

        # Remaining payment $60 -> auto-settles to PAID
        Payment.objects.create(
            invoice=inv,
            amount=Decimal('60.00'),
            payment_method=Payment.PaymentMethod.BANK_TRANSFER
        )
        inv.refresh_from_db()
        self.assertEqual(inv.paid_amount, Decimal('100.00'))
        self.assertEqual(inv.balance_due, Decimal('0.00'))
        self.assertEqual(inv.status, Invoice.Status.PAID)
