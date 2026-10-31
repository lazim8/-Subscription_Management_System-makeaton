from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User
from catalog.models import Product, ProductVariant
from billing.models import Tax, Subscription, Invoice, InvoiceLine, Payment


class Command(BaseCommand):
    help = "Seed demonstration invoices across states (Paid, Confirmed, Overdue, Draft) and payments"

    def handle(self, *args, **options):
        sub_acme = Subscription.objects.filter(subscription_number="SUB-2026-0001").first()
        sub_mega = Subscription.objects.filter(subscription_number="SUB-2026-0002").first()
        admin_user = User.objects.filter(role=User.Role.ADMIN).first()
        vat = Tax.objects.filter(name__icontains="VAT").first()
        crm_prod = Product.objects.filter(name="Brightloop CRM Core").first()
        v_odoo = ProductVariant.objects.filter(attribute="Brand", value="Odoo").first()
        p_sla = Product.objects.filter(name="Priority 24/7 SLA Support").first()

        today = date.today()

        # 1. Fully Paid Invoice (INV-2026-0001)
        if sub_acme:
            inv1, created = Invoice.objects.get_or_create(
                invoice_number="INV-2026-0001",
                defaults={
                    'subscription': sub_acme,
                    'customer': sub_acme.customer,
                    'billing_period_start': today - timedelta(days=60),
                    'billing_period_end': today - timedelta(days=30),
                    'issue_date': today - timedelta(days=60),
                    'due_date': today - timedelta(days=60),
                    'status': Invoice.Status.PAID,
                    'subtotal': Decimal('3899.00'),
                    'discount_amount': Decimal('779.80'),
                    'tax_amount': Decimal('311.92'),
                    'total_amount': Decimal('3431.12'),
                    'paid_amount': Decimal('3431.12'),
                    'notes': 'Paid in full via Stripe Card Checkout.'
                }
            )
            if created:
                InvoiceLine.objects.create(
                    invoice=inv1,
                    product=crm_prod,
                    description="Brightloop CRM Core (3 licenses)",
                    quantity=3,
                    unit_price=Decimal('1200.00'),
                    tax_rate=Decimal('10.00'),
                    tax_amount=Decimal('360.00'),
                    line_total=Decimal('3960.00')
                )
                Payment.objects.create(
                    payment_number="PAY-2026-0001",
                    invoice=inv1,
                    amount=Decimal('3431.12'),
                    payment_method=Payment.PaymentMethod.STRIPE,
                    payment_date=today - timedelta(days=59),
                    transaction_reference="ch_3Mxz892104KlpwQ",
                    notes="Automated online credit card settlement",
                    recorded_by=admin_user
                )

        # 2. Confirmed Invoice Awaiting Payment (INV-2026-0002)
        if sub_mega:
            inv2, created = Invoice.objects.get_or_create(
                invoice_number="INV-2026-0002",
                defaults={
                    'subscription': sub_mega,
                    'customer': sub_mega.customer,
                    'billing_period_start': today - timedelta(days=10),
                    'billing_period_end': today + timedelta(days=355),
                    'issue_date': today - timedelta(days=10),
                    'due_date': today + timedelta(days=20),  # Net 30 -> Still 20 days left
                    'status': Invoice.Status.CONFIRMED,
                    'subtotal': Decimal('21319.00'),
                    'discount_amount': Decimal('100.00'),
                    'tax_amount': Decimal('2121.90'),
                    'total_amount': Decimal('23340.90'),
                    'paid_amount': Decimal('0.00'),
                    'notes': 'Net 30 invoice dispatched to corporate accounts payable.'
                }
            )
            if created:
                InvoiceLine.objects.create(
                    invoice=inv2,
                    product=crm_prod,
                    variant=v_odoo,
                    description="Brightloop CRM Core (Brand: Odoo, 12 licenses)",
                    quantity=12,
                    unit_price=Decimal('1760.00'),
                    tax_rate=Decimal('10.00'),
                    tax_amount=Decimal('2112.00'),
                    line_total=Decimal('23232.00')
                )

        # 3. Overdue Invoice with Partial Payment (INV-2026-0003)
        if sub_acme:
            inv3, created = Invoice.objects.get_or_create(
                invoice_number="INV-2026-0003",
                defaults={
                    'subscription': sub_acme,
                    'customer': sub_acme.customer,
                    'billing_period_start': today - timedelta(days=50),
                    'billing_period_end': today - timedelta(days=20),
                    'issue_date': today - timedelta(days=50),
                    'due_date': today - timedelta(days=20),  # Due 20 days ago -> Overdue!
                    'status': Invoice.Status.CONFIRMED,
                    'subtotal': Decimal('1200.00'),
                    'discount_amount': Decimal('0.00'),
                    'tax_amount': Decimal('120.00'),
                    'total_amount': Decimal('1320.00'),
                    'paid_amount': Decimal('500.00'),
                    'notes': 'Overdue invoice; partial payment of $500 received via wire transfer.'
                }
            )
            if created:
                InvoiceLine.objects.create(
                    invoice=inv3,
                    product=crm_prod,
                    description="Brightloop CRM Core (1 license)",
                    quantity=1,
                    unit_price=Decimal('1200.00'),
                    tax_rate=Decimal('10.00'),
                    tax_amount=Decimal('120.00'),
                    line_total=Decimal('1320.00')
                )
                Payment.objects.create(
                    payment_number="PAY-2026-0002",
                    invoice=inv3,
                    amount=Decimal('500.00'),
                    payment_method=Payment.PaymentMethod.BANK_TRANSFER,
                    payment_date=today - timedelta(days=15),
                    transaction_reference="WIRE-78921-PARTIAL",
                    notes="Partial advance wire transfer",
                    recorded_by=admin_user
                )

        # 4. Draft Invoice (INV-2026-0004)
        if sub_acme:
            inv4, created = Invoice.objects.get_or_create(
                invoice_number="INV-2026-0004",
                defaults={
                    'subscription': sub_acme,
                    'customer': sub_acme.customer,
                    'billing_period_start': today,
                    'billing_period_end': today + timedelta(days=30),
                    'issue_date': today,
                    'due_date': today,
                    'status': Invoice.Status.DRAFT,
                    'subtotal': Decimal('299.00'),
                    'discount_amount': Decimal('0.00'),
                    'tax_amount': Decimal('29.90'),
                    'total_amount': Decimal('328.90'),
                    'paid_amount': Decimal('0.00'),
                    'notes': 'Draft review before dispatch.'
                }
            )
            if created:
                p_db = Product.objects.filter(name="Dedicated Database Cluster").first()
                if p_db:
                    InvoiceLine.objects.create(
                        invoice=inv4,
                        product=p_db,
                        description="Dedicated Database Cluster Addon",
                        quantity=1,
                        unit_price=Decimal('299.00'),
                        tax_rate=Decimal('10.00'),
                        tax_amount=Decimal('29.90'),
                        line_total=Decimal('328.90')
                    )

        self.stdout.write(self.style.SUCCESS("Demonstration invoices and payments seeded successfully."))
