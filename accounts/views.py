"""
Brightloop Accounts Views.
Handles authentication, registration, role-based views, staff management, and profile editing.
"""
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from django.db.models import Q
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from .forms import CustomerSignupForm, StaffCreationForm, CustomLoginForm, UserProfileForm
from .mixins import AdminRequiredMixin, StaffRequiredMixin
from .models import User


class CustomerSignupView(View):
    """
    Public customer signup.
    Enforces unique email, strong password (>8 chars, uppercase, lowercase, special char).
    """
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard' if request.user.role != 'customer' else 'billing:customer-portal-subscriptions')
        form = CustomerSignupForm()
        return render(request, 'accounts/signup.html', {'form': form})

    def post(self, request):
        form = CustomerSignupForm(request.data if hasattr(request, 'data') else request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Brightloop, {user.first_name or user.email}! Your customer portal is ready.")
            return redirect('billing:customer-portal-subscriptions')
        return render(request, 'accounts/signup.html', {'form': form})


class CustomLoginView(View):
    """
    Login view using email as the login credential.
    Directs admin/staff to the operations dashboard, and customers to their self-service portal.
    """
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('dashboard' if request.user.role != 'customer' else 'billing:customer-portal-subscriptions')
        form = CustomLoginForm()
        return render(request, 'accounts/login.html', {'form': form})

    def post(self, request):
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            messages.success(request, f"Signed in successfully as {user.email}.")
            
            # Check for ?next= redirect
            next_url = request.GET.get('next')
            if next_url:
                return redirect(next_url)

            # Direct by role
            if user.role in ['admin', 'staff']:
                return redirect('dashboard')
            return redirect('billing:customer-portal-subscriptions')

        return render(request, 'accounts/login.html', {'form': form})


class CustomLogoutView(View):
    """
    Logs out user and redirects to login page.
    """
    def post(self, request):
        logout(request)
        messages.info(request, "You have been signed out.")
        return redirect('accounts:login')


class StaffListCreateView(AdminRequiredMixin, View):
    """
    Admin-only page to view and create internal staff members.
    Strict Security Rule: Only Admin can add staff.
    """
    def get(self, request):
        staff_list = User.objects.filter(role=User.Role.STAFF).order_by('-date_joined')
        form = StaffCreationForm()
        return render(request, 'accounts/staff_list_create.html', {
            'staff_list': staff_list,
            'form': form,
        })

    def post(self, request):
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            staff_member = form.save()
            messages.success(request, f"Staff account created for {staff_member.email}.")
            return redirect('accounts:staff-list-create')
        
        staff_list = User.objects.filter(role=User.Role.STAFF).order_by('-date_joined')
        return render(request, 'accounts/staff_list_create.html', {
            'staff_list': staff_list,
            'form': form,
        })


class CustomerListView(StaffRequiredMixin, ListView):
    """
    Staff/Admin view listing all registered customers with search and pagination (25 per page).
    """
    model = User
    template_name = 'accounts/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        qs = User.objects.filter(role=User.Role.CUSTOMER).order_by('-date_joined')
        search_query = self.request.GET.get('q', '').strip()
        if search_query:
            qs = qs.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(company_name__icontains=search_query)
            )
        return qs


class UserProfileView(LoginRequiredMixin, UpdateView):
    """
    Allows any authenticated user to view and update their profile details.
    """
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile details have been updated.")
        return super().form_valid(form)


# --- Password Reset Flow (using Django console backend) ---
class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password-reset-done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password-reset-complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'
