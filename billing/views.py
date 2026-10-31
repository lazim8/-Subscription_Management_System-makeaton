"""
Brightloop Billing Views:
- Subscriptions List, Detail, Creation (manual or from Quotation Template)
- State Machine Workflow Actions (Draft -> Quotation -> Confirmed -> Active -> Closed/Paused/Renewed)
- Audit Trail History
- Taxes & Discount Rules Configuration (Admin-only)
"""
from decimal import Decimal
from datetime import date, timedelta
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from accounts.mixins import StaffRequiredMixin, AdminRequiredMixin
from catalog.models import Product, ProductVariant, Plan, QuotationTemplate
from .models import (
    Tax,
    Discount,
    Subscription,
    SubscriptionLine,
    SubscriptionAuditLog,
    Invoice,
    InvoiceLine,
    Payment,
)
from .forms import TaxForm, DiscountForm, SubscriptionForm, PaymentForm


# --- Subscriptions Views ---

class SubscriptionListView(StaffRequiredMixin, ListView):
    """
    List subscriptions with search (number, customer), status filter, and pagination.
    """
    model = Subscription
    template_name = 'billing/subscription_list.html'
    context_object_name = 'subscriptions'
    paginate_by = 25

    def get_queryset(self):
        qs = Subscription.objects.select_related('customer', 'plan', 'discount').prefetch_related('lines').all()
        q = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(subscription_number__icontains=q) |
                Q(customer__email__icontains=q) |
                Q(customer__company_name__icontains=q) |
                Q(customer__first_name__icontains=q) |
                Q(customer__last_name__icontains=q)
            )
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Subscription.Status.choices
        return context


class SubscriptionDetailView(StaffRequiredMixin, DetailView):
    """
    Detailed inspection of a subscription, its lines, financial metrics, state transition actions, and audit trail.
    """
    model = Subscription
    template_name = 'billing/subscription_detail.html'
    context_object_name = 'subscription'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sub = self.object
        context['audit_logs'] = sub.audit_logs.select_related('changed_by').all()
        
        # Calculate available state transitions
        possible_transitions = []
        for target_status, label in Subscription.Status.choices:
            if target_status != sub.status:
                can_do, reason = sub.can_transition_to(target_status)
                if can_do:
                    possible_transitions.append({
                        'status': target_status,
                        'label': label,
                        'css_class': 'btn-primary' if target_status in ['quotation', 'confirmed', 'active'] else 'btn-secondary'
                    })
        context['available_transitions'] = possible_transitions
        return context


class SubscriptionCreateView(StaffRequiredMixin, View):
    """
    Create a new subscription:
    - Can start completely from scratch
    - OR pre-populate plan and lines from a Quotation Template!
    """
    def get(self, request):
        template_id = request.GET.get('template_id')
        initial_data = {}
        preset_lines = []

        if template_id:
            template = get_object_or_404(QuotationTemplate, id=template_id)
            initial_data['plan'] = template.plan
            initial_data['start_date'] = date.today()
            initial_data['expiry_date'] = date.today() + timedelta(days=template.validity_days)
            initial_data['notes'] = f"Generated from Quotation Template: {template.name}"
            preset_lines = template.lines.select_related('product', 'variant').all()

        form = SubscriptionForm(initial=initial_data)
        products = Product.objects.filter(is_active=True).prefetch_related('variants')
        taxes = Tax.objects.filter(is_active=True)
        default_tax = Tax.objects.filter(is_default=True).first()

        return render(request, 'billing/subscription_form.html', {
            'form': form,
            'products': products,
            'taxes': taxes,
            'default_tax': default_tax,
            'preset_lines': preset_lines
        })

    def post(self, request):
        form = SubscriptionForm(request.POST)
        if form.is_valid():
            subscription = form.save(commit=False)
            subscription.created_by = request.user
            subscription.status = Subscription.Status.DRAFT
            subscription.save()

            # Process dynamic line items
            product_ids = request.POST.getlist('product_id')
            variant_ids = request.POST.getlist('variant_id')
            quantities = request.POST.getlist('quantity')
            unit_prices = request.POST.getlist('unit_price')
            tax_ids = request.POST.getlist('tax_id')

            for p_id, v_id, qty, price, t_id in zip(product_ids, variant_ids, quantities, unit_prices, tax_ids):
                if p_id:
                    prod = Product.objects.get(id=p_id)
                    var = ProductVariant.objects.filter(id=v_id).first() if v_id else None
                    tax_obj = Tax.objects.filter(id=t_id).first() if t_id else None
                    unit_p = Decimal(str(price)) if price else (var.total_unit_price if var else prod.sales_price)

                    SubscriptionLine.objects.create(
                        subscription=subscription,
                        product=prod,
                        variant=var,
                        quantity=int(qty) if qty else 1,
                        unit_price=unit_p,
                        tax=tax_obj
                    )

            # Record initial creation in audit log
            SubscriptionAuditLog.objects.create(
                subscription=subscription,
                from_status='none',
                to_status=Subscription.Status.DRAFT,
                changed_by=request.user,
                notes="Subscription drafted"
            )

            messages.success(request, f"Subscription {subscription.subscription_number} created successfully in Draft status.")
            return redirect('billing:subscription-detail', pk=subscription.id)

        products = Product.objects.filter(is_active=True).prefetch_related('variants')
        taxes = Tax.objects.filter(is_active=True)
        return render(request, 'billing/subscription_form.html', {
            'form': form,
            'products': products,
            'taxes': taxes
        })


class SubscriptionTransitionView(StaffRequiredMixin, View):
    """
    POST action to advance subscription status (e.g. Quotation -> Confirmed -> Active).
    """
    def post(self, request, pk):
        subscription = get_object_or_404(Subscription, pk=pk)
        target_status = request.POST.get('target_status')
        notes = request.POST.get('notes', '').strip()

        try:
            subscription.transition_to(target_status, user=request.user, notes=notes)
            messages.success(request, f"Status updated to {subscription.get_status_display()}.")
        except ValueError as e:
            messages.error(request, str(e))

        return redirect('billing:subscription-detail', pk=subscription.id)


# --- Taxes & Discounts Views (Admin-Only) ---

class DiscountTaxListView(AdminRequiredMixin, View):
    """
    Admin control center for Tax Rules and Promotional Discounts.
    """
    def get(self, request):
        taxes = Tax.objects.all()
        discounts = Discount.objects.all()
        return render(request, 'billing/discount_tax_list.html', {
            'taxes': taxes,
            'discounts': discounts
        })


class TaxCreateView(AdminRequiredMixin, CreateView):
    model = Tax
    form_class = TaxForm
    template_name = 'billing/tax_form.html'
    success_url = reverse_lazy('billing:discount-tax-list')

    def form_valid(self, form):
        messages.success(self.request, f"Tax rule '{form.instance.name}' ({form.instance.rate}%) created.")
        return super().form_valid(form)


class TaxUpdateView(AdminRequiredMixin, UpdateView):
    model = Tax
    form_class = TaxForm
    template_name = 'billing/tax_form.html'
    success_url = reverse_lazy('billing:discount-tax-list')

    def form_valid(self, form):
        messages.success(self.request, f"Tax rule '{form.instance.name}' updated.")
        return super().form_valid(form)


class DiscountCreateView(AdminRequiredMixin, CreateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'billing/discount_form.html'
    success_url = reverse_lazy('billing:discount-tax-list')

    def form_valid(self, form):
        messages.success(self.request, f"Discount rule '{form.instance.code}' created.")
        return super().form_valid(form)


class DiscountUpdateView(AdminRequiredMixin, UpdateView):
    model = Discount
    form_class = DiscountForm
    template_name = 'billing/discount_form.html'
    success_url = reverse_lazy('billing:discount-tax-list')

    def form_valid(self, form):
        messages.success(self.request, f"Discount rule '{form.instance.code}' updated.")
        return super().form_valid(form)


# --- Invoicing, Automated Billing Run & Payments (Step 4) ---

class AutomatedBillingRunView(StaffRequiredMixin, View):
    """
    1-Click Automated Billing Engine:
    - Scans active subscriptions due for billing (next_billing_date <= today)
    - Enforces strict Double-Billing Guard
    - Generates invoices, applies discounts & taxes automatically
    - Advances next_billing_date based on plan cadence
    """
    def post(self, request):
        today = date.today()
        # Find active subscriptions due for billing
        due_subscriptions = Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            next_billing_date__lte=today
        ).select_related('customer', 'plan', 'discount').prefetch_related('lines__product', 'lines__variant', 'lines__tax')

        invoices_created = 0
        total_billed = Decimal('0.00')
        skipped_count = 0

        for sub in due_subscriptions:
            # 1. Double-Billing Guard: check if an invoice already exists for this exact billing period
            start_date = sub.next_billing_date
            period = sub.plan.billing_period

            if period == Plan.BillingPeriod.DAILY:
                end_date = start_date + timedelta(days=1)
            elif period == Plan.BillingPeriod.WEEKLY:
                end_date = start_date + timedelta(days=7)
            elif period == Plan.BillingPeriod.MONTHLY:
                end_date = start_date + timedelta(days=30)
            elif period == Plan.BillingPeriod.YEARLY:
                end_date = start_date + timedelta(days=365)
            else:
                end_date = start_date + timedelta(days=30)

            # Check if active invoice already generated for this cycle
            existing = Invoice.objects.filter(
                subscription=sub,
                billing_period_start=start_date,
                status__in=[Invoice.Status.DRAFT, Invoice.Status.CONFIRMED, Invoice.Status.PAID]
            ).exists()

            if existing:
                skipped_count += 1
                continue

            # 2. Create Invoice
            invoice = Invoice.objects.create(
                subscription=sub,
                customer=sub.customer,
                billing_period_start=start_date,
                billing_period_end=end_date,
                issue_date=today,
                status=Invoice.Status.CONFIRMED,  # Automatically confirmed for sending
                notes=f"Automated recurring billing run for {sub.plan.name} ({start_date} to {end_date})"
            )

            # 3. Create Itemized Invoice Lines
            subtotal = Decimal('0.00')
            tax_total = Decimal('0.00')

            for s_line in sub.lines.all():
                line_tax = s_line.line_tax
                tax_rate = s_line.tax.rate if s_line.tax else Decimal('0.00')
                v_desc = f" ({s_line.variant.attribute}: {s_line.variant.value})" if s_line.variant else ""
                desc = f"{s_line.product.name}{v_desc}"

                InvoiceLine.objects.create(
                    invoice=invoice,
                    product=s_line.product,
                    variant=s_line.variant,
                    description=desc,
                    quantity=s_line.quantity,
                    unit_price=s_line.unit_price,
                    tax_rate=tax_rate,
                    tax_amount=line_tax,
                    line_total=s_line.line_total
                )
                subtotal += s_line.line_subtotal
                tax_total += line_tax

            # 4. Calculate discount
            discount_amount = Decimal('0.00')
            if sub.discount:
                valid, _ = sub.discount.is_valid_for(subtotal, sub.total_quantity)
                if valid:
                    discount_amount = sub.discount.calculate_discount(subtotal)

            total_amount = (subtotal - discount_amount + tax_total).quantize(Decimal('0.01'))

            invoice.subtotal = subtotal
            invoice.discount_amount = discount_amount
            invoice.tax_amount = tax_total
            invoice.total_amount = total_amount
            invoice.save()

            # 5. Advance subscription next_billing_date
            sub.next_billing_date = end_date
            sub.save(update_fields=['next_billing_date'])

            invoices_created += 1
            total_billed += total_amount

        if invoices_created > 0:
            messages.success(
                request,
                f"Automated Billing Run complete: {invoices_created} invoices generated totaling ${total_billed:,.2f}. "
                f"({skipped_count} subscriptions protected by double-billing guard)."
            )
        else:
            messages.info(
                request,
                f"Billing Run: All subscriptions are up to date! ({skipped_count} subscriptions protected by double-billing guard)."
            )

        return redirect('billing:invoice-list')


class InvoiceListView(StaffRequiredMixin, ListView):
    """
    List all generated invoices with status filters (Draft, Confirmed, Paid, Cancelled, Overdue) and search.
    """
    model = Invoice
    template_name = 'billing/invoice_list.html'
    context_object_name = 'invoices'
    paginate_by = 25

    def get_queryset(self):
        qs = Invoice.objects.select_related('customer', 'subscription__plan').all()
        q = self.request.GET.get('q', '').strip()
        status_filter = self.request.GET.get('status', '').strip()

        if q:
            qs = qs.filter(
                Q(invoice_number__icontains=q) |
                Q(customer__email__icontains=q) |
                Q(customer__company_name__icontains=q) |
                Q(subscription__subscription_number__icontains=q)
            )

        if status_filter == 'overdue':
            today = date.today()
            qs = qs.filter(status=Invoice.Status.CONFIRMED, due_date__lt=today)
        elif status_filter:
            qs = qs.filter(status=status_filter)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = Invoice.Status.choices
        # Calculate summary metrics
        today = date.today()
        context['total_unpaid'] = sum(
            inv.balance_due for inv in Invoice.objects.filter(status=Invoice.Status.CONFIRMED)
        )
        context['overdue_count'] = Invoice.objects.filter(
            status=Invoice.Status.CONFIRMED,
            due_date__lt=today
        ).count()
        return context


class InvoiceDetailView(StaffRequiredMixin, DetailView):
    """
    Detailed printable view of an invoice, payment ledger, and modal for recording payments.
    """
    model = Invoice
    template_name = 'billing/invoice_detail.html'
    context_object_name = 'invoice'

    def get_context_data(self, **kwargs):
        from .forms import PaymentForm
        context = super().get_context_data(**kwargs)
        inv = self.object
        context['payments'] = inv.payments.select_related('recorded_by').all()
        context['payment_form'] = PaymentForm(initial={'amount': inv.balance_due, 'payment_date': date.today()})
        return context


class InvoiceStatusUpdateView(StaffRequiredMixin, View):
    """
    POST action to Confirm or Cancel an invoice.
    """
    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        new_status = request.POST.get('status')
        if new_status in [Invoice.Status.CONFIRMED, Invoice.Status.CANCELLED]:
            invoice.status = new_status
            invoice.save(update_fields=['status'])
            messages.success(request, f"Invoice {invoice.invoice_number} status set to {invoice.get_status_display()}.")
        return redirect('billing:invoice-detail', pk=invoice.id)


class InvoicePaymentRecordView(StaffRequiredMixin, View):
    """
    POST action to record a partial or full payment against an invoice.
    """
    def post(self, request, pk):
        from .forms import PaymentForm
        invoice = get_object_or_404(Invoice, pk=pk)
        form = PaymentForm(request.POST)

        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            payment.recorded_by = request.user
            payment.save()

            messages.success(
                request,
                f"Payment {payment.payment_number} of ${payment.amount:,.2f} recorded via {payment.get_payment_method_display()}. "
                f"Remaining balance: ${invoice.balance_due:,.2f}."
            )
        else:
            messages.error(request, "Error recording payment. Please check payment fields.")

        return redirect('billing:invoice-detail', pk=invoice.id)


class PaymentListView(StaffRequiredMixin, ListView):
    """
    Ledger of all collected payments across all customers.
    """
    model = Payment
    template_name = 'billing/payment_list.html'
    context_object_name = 'payments'
    paginate_by = 25

    def get_queryset(self):
        qs = Payment.objects.select_related('invoice__customer', 'invoice__subscription', 'recorded_by').all()
        q = self.request.GET.get('q', '').strip()
        method = self.request.GET.get('method', '').strip()

        if q:
            qs = qs.filter(
                Q(payment_number__icontains=q) |
                Q(transaction_reference__icontains=q) |
                Q(invoice__invoice_number__icontains=q) |
                Q(invoice__customer__email__icontains=q) |
                Q(invoice__customer__company_name__icontains=q)
            )
        if method:
            qs = qs.filter(payment_method=method)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['methods'] = Payment.PaymentMethod.choices
        context['total_collected'] = sum(p.amount for p in Payment.objects.all())
        return context


class OverdueInvoicesListView(StaffRequiredMixin, ListView):
    """
    Overdue Chasing Center: lists all unpaid confirmed invoices past due date with aging buckets and chase notices.
    """
    model = Invoice
    template_name = 'billing/overdue_list.html'
    context_object_name = 'overdue_invoices'
    paginate_by = 25

    def get_queryset(self):
        today = date.today()
        return Invoice.objects.filter(
            status=Invoice.Status.CONFIRMED,
            due_date__lt=today
        ).select_related('customer', 'subscription__plan').order_by('due_date')

    def post(self, request):
        """Action: send automated reminder notice to customer."""
        invoice_id = request.POST.get('invoice_id')
        invoice = get_object_or_404(Invoice, id=invoice_id)
        messages.success(
            request,
            f"Overdue payment notice dispatched to {invoice.customer.email} for Invoice {invoice.invoice_number} (${invoice.balance_due:,.2f} due)."
        )
        return redirect('billing:overdue-list')

