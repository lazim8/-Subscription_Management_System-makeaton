from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsSystemAdmin(BasePermission):
    """
    Allows access only to System Administrators.
    Required for:
    - Adding new staff members
    - Setting up products, plans, taxes, discount rules
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'admin' or request.user.is_superuser)
        )


class IsInternalStaff(BasePermission):
    """
    Allows access to Internal Staff and Admins.
    Required for:
    - Daily operations: Quotations, Subscriptions, Billing runs, Payments recording
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role in ['admin', 'staff'] or request.user.is_staff or request.user.is_superuser)
        )


class IsCustomer(BasePermission):
    """
    Allows access to Customers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.role == 'customer'
        )


class IsOwnerOrStaff(BasePermission):
    """
    Object-level permission allowing staff full access,
    and customers access only to their own resources.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Staff and admins have full access
        if request.user.role in ['admin', 'staff'] or request.user.is_staff or request.user.is_superuser:
            return True

        # Check customer ownership
        customer_attr = getattr(obj, 'customer', None) or getattr(obj, 'user', None)
        if customer_attr:
            return customer_attr == request.user

        return False
