"""
Brightloop Role-Based Access Control Mixins.
Provides clean, reusable access checks for Django class-based views.
"""
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Base mixin ensuring the user is logged in and belongs to one of allowed_roles.
    """
    allowed_roles = []

    def test_func(self):
        user = self.request.user
        if not user.is_authenticated:
            return False
        # Superuser always has access
        if user.is_superuser:
            return True
        return user.role in self.allowed_roles

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied("You do not have permission to access this resource.")
        return super().handle_no_permission()


class AdminRequiredMixin(RoleRequiredMixin):
    """
    Restricts access strictly to System Administrators.
    Only admin can:
    - Add staff members
    - Create/modify products, plans, taxes, discounts
    - View executive reports
    """
    allowed_roles = ['admin']


class StaffRequiredMixin(RoleRequiredMixin):
    """
    Allows access to Internal Staff and Admins.
    Used for day-to-day operations:
    - View/manage customers, subscriptions, invoices, payments
    """
    allowed_roles = ['admin', 'staff']


class CustomerRequiredMixin(RoleRequiredMixin):
    """
    Restricts access to Customer Portal views.
    """
    allowed_roles = ['customer']


class CustomerQuerysetFilterMixin:
    """
    Reusable queryset filter:
    - If customer logs in: filter queryset so they see ONLY their own records.
    - If staff/admin logs in: return full queryset.
    """
    customer_field_name = 'customer'

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.is_authenticated and user.role == 'customer':
            filter_kwargs = {self.customer_field_name: user}
            return qs.filter(**filter_kwargs)
        return qs
