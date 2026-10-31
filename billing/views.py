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
from .models import Tax, Discount, Subscription, SubscriptionLine, SubscriptionAuditLog
from .forms import TaxForm, DiscountForm, SubscriptionForm


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
