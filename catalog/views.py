"""
Brightloop Catalog Views.
Provides views for Products, Variants, Plans, and Quotation Templates.
Staff can view; only Admin can create and modify products & plans.
"""
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DetailView, DeleteView

from accounts.mixins import StaffRequiredMixin, AdminRequiredMixin
from .models import Product, ProductVariant, Plan, QuotationTemplate, QuotationTemplateLine
from .forms import ProductForm, ProductVariantForm, PlanForm, QuotationTemplateForm


# --- Products Views ---

class ProductListView(StaffRequiredMixin, ListView):
    """
    List all products with search and active status filters.
    """
    model = Product
    template_name = 'catalog/product_list.html'
    context_object_name = 'products'
    paginate_by = 25

    def get_queryset(self):
        qs = Product.objects.prefetch_related('variants').all()
        q = self.request.GET.get('q', '').strip()
        p_type = self.request.GET.get('type', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(notes__icontains=q))
        if p_type:
            qs = qs.filter(product_type=p_type)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_types'] = Product.ProductType.choices
        return context


class ProductCreateView(AdminRequiredMixin, CreateView):
    """
    Admin-only: create a new product.
    """
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product-list')

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' created successfully.")
        return super().form_valid(form)


class ProductUpdateView(AdminRequiredMixin, UpdateView):
    """
    Admin-only: update product details and manage its variants.
    """
    model = Product
    form_class = ProductForm
    template_name = 'catalog/product_form.html'
    success_url = reverse_lazy('catalog:product-list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['variant_form'] = ProductVariantForm()
        context['variants'] = self.object.variants.all()
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Product '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class ProductVariantCreateView(AdminRequiredMixin, View):
    """
    Admin-only: add a variant (e.g. Brand / Odoo / +560) to a product.
    """
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        form = ProductVariantForm(request.POST)
        if form.is_valid():
            variant = form.save(commit=False)
            variant.product = product
            variant.save()
            messages.success(request, f"Variant '{variant.attribute}: {variant.value}' added (+${variant.extra_price}).")
        else:
            messages.error(request, "Failed to add variant. Check variant fields.")
        return redirect('catalog:product-edit', pk=product.id)


class ProductVariantDeleteView(AdminRequiredMixin, DeleteView):
    """
    Admin-only: remove a product variant.
    """
    model = ProductVariant

    def get_success_url(self):
        product_id = self.object.product.id
        messages.info(self.request, "Variant removed.")
        return reverse('catalog:product-edit', kwargs={'pk': product_id})


# --- Plans Views ---

class PlanListView(StaffRequiredMixin, ListView):
    """
    List all billing plans with cadence and lifecycle flags.
    """
    model = Plan
    template_name = 'catalog/plan_list.html'
    context_object_name = 'plans'
    paginate_by = 25

    def get_queryset(self):
        qs = Plan.objects.all()
        q = self.request.GET.get('q', '').strip()
        period = self.request.GET.get('period', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)
        if period:
            qs = qs.filter(billing_period=period)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['billing_periods'] = Plan.BillingPeriod.choices
        return context


class PlanCreateView(AdminRequiredMixin, CreateView):
    """
    Admin-only: configure and launch a new billing plan.
    """
    model = Plan
    form_class = PlanForm
    template_name = 'catalog/plan_form.html'
    success_url = reverse_lazy('catalog:plan-list')

    def form_valid(self, form):
        messages.success(self.request, f"Plan '{form.instance.name}' launched successfully.")
        return super().form_valid(form)


class PlanUpdateView(AdminRequiredMixin, UpdateView):
    """
    Admin-only: update plan settings and lifecycle flags.
    """
    model = Plan
    form_class = PlanForm
    template_name = 'catalog/plan_form.html'
    success_url = reverse_lazy('catalog:plan-list')

    def form_valid(self, form):
        messages.success(self.request, f"Plan '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


# --- Quotation Templates Views ---

class QuotationTemplateListView(StaffRequiredMixin, ListView):
    """
    List all quotation templates available to sales reps.
    """
    model = QuotationTemplate
    template_name = 'catalog/quotation_template_list.html'
    context_object_name = 'templates'
    paginate_by = 25

    def get_queryset(self):
        return QuotationTemplate.objects.select_related('plan').prefetch_related('lines__product', 'lines__variant').all()


class QuotationTemplateCreateView(StaffRequiredMixin, View):
    """
    Create a new Quotation Template with plan and preset line items.
    """
    def get(self, request):
        form = QuotationTemplateForm()
        products = Product.objects.filter(is_active=True).prefetch_related('variants')
        return render(request, 'catalog/quotation_template_form.html', {
            'form': form,
            'products': products
        })

    def post(self, request):
        form = QuotationTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            # Process dynamic line items submitted
            product_ids = request.POST.getlist('product_id')
            variant_ids = request.POST.getlist('variant_id')
            quantities = request.POST.getlist('quantity')

            for p_id, v_id, qty in zip(product_ids, variant_ids, quantities):
                if p_id:
                    prod = Product.objects.get(id=p_id)
                    var = ProductVariant.objects.filter(id=v_id).first() if v_id else None
                    unit_p = var.total_unit_price if var else prod.sales_price
                    QuotationTemplateLine.objects.create(
                        template=template,
                        product=prod,
                        variant=var,
                        quantity=int(qty) if qty else 1,
                        unit_price=unit_p
                    )

            messages.success(request, f"Quotation Template '{template.name}' created.")
            return redirect('catalog:quotation-template-list')

        products = Product.objects.filter(is_active=True).prefetch_related('variants')
        return render(request, 'catalog/quotation_template_form.html', {
            'form': form,
            'products': products
        })


class QuotationTemplateDetailView(StaffRequiredMixin, DetailView):
    """
    Inspect quotation template details and lines before generating a quote.
    """
    model = QuotationTemplate
    template_name = 'catalog/quotation_template_detail.html'
    context_object_name = 'template'
