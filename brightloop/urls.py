"""
URL configuration for brightloop project.
"""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from billing.views import DashboardView


def root_redirect(request):
    if request.user.is_authenticated:
        if request.user.role in ['admin', 'staff']:
            return redirect('dashboard')
        return redirect('billing:customer-portal-subscriptions')
    return redirect('accounts:login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect, name='root'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('accounts/', include('accounts.urls')),
    path('catalog/', include('catalog.urls')),
    path('billing/', include('billing.urls')),
]
