from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from catalog.models import Product, ProductVariant, Plan, QuotationTemplate, QuotationTemplateLine


class Command(BaseCommand):
    help = "Seed initial products, variants (Odoo brand +560), plans, and quotation templates"

    def handle(self, *args, **options):
        # 1. Products
        p1, _ = Product.objects.get_or_create(
            name="Brightloop CRM Core",
            defaults={
                'product_type': Product.ProductType.SOFTWARE,
                'sales_price': Decimal('1200.00'),
                'cost_price': Decimal('350.00'),
                'notes': 'Core enterprise CRM with recurring licensing per user seat.'
            }
        )

        # Odoo Brand Variant (+560 as requested in hackathon spec)
        v_odoo, _ = ProductVariant.objects.get_or_create(
            product=p1,
            attribute="Brand",
            value="Odoo",
            defaults={'extra_price': Decimal('560.00')}
        )
        v_std, _ = ProductVariant.objects.get_or_create(
            product=p1,
            attribute="Brand",
            value="Standard",
            defaults={'extra_price': Decimal('0.00')}
        )

        p2, _ = Product.objects.get_or_create(
            name="Analytics & Forecasting Suite",
            defaults={
                'product_type': Product.ProductType.SOFTWARE,
                'sales_price': Decimal('450.00'),
                'cost_price': Decimal('100.00'),
                'notes': 'Real-time telemetry and revenue forecasting module.'
            }
        )

        p3, _ = Product.objects.get_or_create(
            name="Dedicated Database Cluster",
            defaults={
                'product_type': Product.ProductType.ADDON,
                'sales_price': Decimal('299.00'),
                'cost_price': Decimal('80.00'),
                'notes': 'Customer togglable isolated database node with zero noisy neighbors.'
            }
        )

        p4, _ = Product.objects.get_or_create(
            name="Priority 24/7 SLA Support",
            defaults={
                'product_type': Product.ProductType.ADDON,
                'sales_price': Decimal('199.00'),
                'cost_price': Decimal('40.00'),
                'notes': 'Sub-15 minute response guarantee with direct Slack channel.'
            }
        )

        p5, _ = Product.objects.get_or_create(
            name="Enterprise Onboarding & Consulting",
            defaults={
                'product_type': Product.ProductType.SERVICE,
                'sales_price': Decimal('2500.00'),
                'cost_price': Decimal('900.00'),
                'notes': 'Full setup, workflow automation, and data migration.'
            }
        )
        self.stdout.write(self.style.SUCCESS("Products and variants seeded successfully."))

        # 2. Plans
        plan_monthly, _ = Plan.objects.get_or_create(
            name="Startup Monthly",
            defaults={
                'price': Decimal('199.00'),
                'billing_period': Plan.BillingPeriod.MONTHLY,
                'min_quantity': 1,
                'available_from': date(2026, 1, 1),
                'auto_close': False,
                'closable': True,
                'pausable': True,
                'renewable': True
            }
        )

        plan_weekly, _ = Plan.objects.get_or_create(
            name="Pro Weekly Sprint",
            defaults={
                'price': Decimal('75.00'),
                'billing_period': Plan.BillingPeriod.WEEKLY,
                'min_quantity': 1,
                'available_from': date(2026, 1, 1),
                'auto_close': False,
                'closable': True,
                'pausable': True,
                'renewable': True
            }
        )

        plan_annual, _ = Plan.objects.get_or_create(
            name="Enterprise Annual Solution",
            defaults={
                'price': Decimal('1890.00'),
                'billing_period': Plan.BillingPeriod.YEARLY,
                'min_quantity': 5,
                'available_from': date(2026, 1, 1),
                'auto_close': False,
                'closable': True,
                'pausable': True,
                'renewable': True
            }
        )

        plan_daily, _ = Plan.objects.get_or_create(
            name="Pilot Trial (Daily)",
            defaults={
                'price': Decimal('25.00'),
                'billing_period': Plan.BillingPeriod.DAILY,
                'min_quantity': 1,
                'available_from': date(2026, 1, 1),
                'auto_close': True,
                'closable': True,
                'pausable': False,
                'renewable': False
            }
        )
        self.stdout.write(self.style.SUCCESS("Billing plans seeded successfully."))

        # 3. Quotation Templates
        t1, _ = QuotationTemplate.objects.get_or_create(
            name="Enterprise Annual Solution Quote",
            defaults={
                'plan': plan_annual,
                'validity_days': 30,
                'description': 'Comprehensive corporate offer bundling Brightloop CRM with Odoo variant and 24/7 SLA.'
            }
        )
        if not t1.lines.exists():
            QuotationTemplateLine.objects.create(
                template=t1,
                product=p1,
                variant=v_odoo,
                quantity=10,
                unit_price=v_odoo.total_unit_price  # 1200 + 560 = 1760.00
            )
            QuotationTemplateLine.objects.create(
                template=t1,
                product=p4,
                quantity=1,
                unit_price=p4.sales_price
            )

        t2, _ = QuotationTemplate.objects.get_or_create(
            name="Standard SaaS Starter Quote",
            defaults={
                'plan': plan_monthly,
                'validity_days': 15,
                'description': 'Starter bundle for small businesses taking CRM and Analytics modules.'
            }
        )
        if not t2.lines.exists():
            QuotationTemplateLine.objects.create(
                template=t2,
                product=p1,
                variant=v_std,
                quantity=2,
                unit_price=p1.sales_price
            )
            QuotationTemplateLine.objects.create(
                template=t2,
                product=p2,
                quantity=1,
                unit_price=p2.sales_price
            )

        self.stdout.write(self.style.SUCCESS("Quotation templates and lines seeded successfully."))
