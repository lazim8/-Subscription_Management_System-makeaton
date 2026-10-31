from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User
from catalog.models import Product, ProductVariant, Plan
from billing.models import Tax, Discount, Subscription, SubscriptionLine, SubscriptionAuditLog


class Command(BaseCommand):
    help = "Seed initial taxes, discounts, and subscriptions across lifecycle states"

    def handle(self, *args, **options):
        # 1. Taxes
        vat, _ = Tax.objects.get_or_create(
            name="Standard VAT (10%)",
            defaults={'rate': Decimal('10.00'), 'is_default': True, 'is_active': True}
        )
        sales_tax, _ = Tax.objects.get_or_create(
            name="State Sales Tax (8.25%)",
            defaults={'rate': Decimal('8.25'), 'is_default': False, 'is_active': True}
        )
        zero_tax, _ = Tax.objects.get_or_create(
            name="Zero Tax Export (0%)",
            defaults={'rate': Decimal('0.00'), 'is_default': False, 'is_active': True}
        )
        self.stdout.write(self.style.SUCCESS("Taxes seeded successfully."))

        # 2. Discounts
        crm_prod = Product.objects.filter(name="Brightloop CRM Core").first()
        d_welcome, _ = Discount.objects.get_or_create(
            code="WELCOME20",
            defaults={
                'name': "New Customer 20% Welcome Offer",
                'discount_type': Discount.DiscountType.PERCENT,
                'value': Decimal('20.00'),
                'target_scope': Discount.TargetScope.SUBSCRIPTION,
                'max_uses': 50,
                'used_count': 1,
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'is_active': True
            }
        )

        d_volume, _ = Discount.objects.get_or_create(
            code="VOLUME100",
            defaults={
                'name': "Volume Tier Discount ($100 Off)",
                'discount_type': Discount.DiscountType.FIXED,
                'value': Decimal('100.00'),
                'target_scope': Discount.TargetScope.SUBSCRIPTION,
                'min_quantity': 5,
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'is_active': True
            }
        )

        d_odoo, _ = Discount.objects.get_or_create(
            code="ODOOSWITCH",
            defaults={
                'name': "Odoo Connected Switcher Promo (15% Off)",
                'discount_type': Discount.DiscountType.PERCENT,
                'value': Decimal('15.00'),
                'target_scope': Discount.TargetScope.PRODUCT,
                'product': crm_prod,
                'start_date': date(2026, 1, 1),
                'end_date': date(2026, 12, 31),
                'is_active': True
            }
        )
        self.stdout.write(self.style.SUCCESS("Discounts seeded successfully."))

        # 3. Subscriptions
        cust_acme = User.objects.filter(email="john@acmeshop.com").first()
        cust_mega = User.objects.filter(email="lisa@megacorp.com").first()
        admin_user = User.objects.filter(role=User.Role.ADMIN).first()

        plan_monthly = Plan.objects.filter(name="Startup Monthly").first()
        plan_annual = Plan.objects.filter(name="Enterprise Annual Solution").first()
        plan_weekly = Plan.objects.filter(name="Pro Weekly Sprint").first()

        p_db = Product.objects.filter(name="Dedicated Database Cluster").first()
        p_sla = Product.objects.filter(name="Priority 24/7 SLA Support").first()
        v_odoo = ProductVariant.objects.filter(attribute="Brand", value="Odoo").first()

        if cust_acme and plan_monthly and crm_prod:
            # Subscription 1: Active
            sub1, created = Subscription.objects.get_or_create(
                subscription_number="SUB-2026-0001",
                defaults={
                    'customer': cust_acme,
                    'plan': plan_monthly,
                    'discount': d_welcome,
                    'payment_terms': Subscription.PaymentTerms.IMMEDIATE,
                    'status': Subscription.Status.ACTIVE,
                    'start_date': date(2026, 10, 1),
                    'expiry_date': date(2027, 10, 1),
                    'next_billing_date': date(2026, 11, 1),
                    'created_by': admin_user
                }
            )
            if created:
                SubscriptionLine.objects.create(
                    subscription=sub1,
                    product=crm_prod,
                    quantity=3,
                    unit_price=crm_prod.sales_price,
                    tax=vat
                )
                if p_db:
                    SubscriptionLine.objects.create(
                        subscription=sub1,
                        product=p_db,
                        quantity=1,
                        unit_price=p_db.sales_price,
                        tax=vat
                    )
                SubscriptionAuditLog.objects.create(
                    subscription=sub1,
                    from_status=Subscription.Status.DRAFT,
                    to_status=Subscription.Status.ACTIVE,
                    changed_by=admin_user,
                    notes="Contract signed and activated"
                )

        if cust_mega and plan_annual and crm_prod:
            # Subscription 2: Quotation
            sub2, created = Subscription.objects.get_or_create(
                subscription_number="SUB-2026-0002",
                defaults={
                    'customer': cust_mega,
                    'plan': plan_annual,
                    'discount': d_volume,
                    'payment_terms': Subscription.PaymentTerms.NET_30,
                    'status': Subscription.Status.QUOTATION,
                    'start_date': date(2026, 10, 15),
                    'expiry_date': date(2026, 11, 14),
                    'next_billing_date': date(2026, 11, 15),
                    'created_by': admin_user,
                    'notes': "Official corporate proposal delivered to procurement lead."
                }
            )
            if created:
                SubscriptionLine.objects.create(
                    subscription=sub2,
                    product=crm_prod,
                    variant=v_odoo,
                    quantity=12,
                    unit_price=v_odoo.total_unit_price if v_odoo else Decimal('1760.00'),
                    tax=vat
                )
                if p_sla:
                    SubscriptionLine.objects.create(
                        subscription=sub2,
                        product=p_sla,
                        quantity=1,
                        unit_price=p_sla.sales_price,
                        tax=vat
                    )
                SubscriptionAuditLog.objects.create(
                    subscription=sub2,
                    from_status=Subscription.Status.DRAFT,
                    to_status=Subscription.Status.QUOTATION,
                    changed_by=admin_user,
                    notes="Quotation dispatched with Net 30 payment terms"
                )

        if cust_acme and plan_weekly and crm_prod:
            # Subscription 3: Draft
            sub3, created = Subscription.objects.get_or_create(
                subscription_number="SUB-2026-0003",
                defaults={
                    'customer': cust_acme,
                    'plan': plan_weekly,
                    'payment_terms': Subscription.PaymentTerms.IMMEDIATE,
                    'status': Subscription.Status.DRAFT,
                    'start_date': date(2026, 10, 31),
                    'expiry_date': date(2027, 10, 31),
                    'next_billing_date': date(2026, 11, 7),
                    'created_by': admin_user
                }
            )
            if created:
                SubscriptionLine.objects.create(
                    subscription=sub3,
                    product=crm_prod,
                    quantity=1,
                    unit_price=crm_prod.sales_price,
                    tax=vat
                )

        self.stdout.write(self.style.SUCCESS("Subscriptions seeded successfully."))
