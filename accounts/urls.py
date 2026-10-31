from django.urls import path
from .views import (
    CustomerSignupView,
    CustomLoginView,
    CustomLogoutView,
    StaffListCreateView,
    CustomerListView,
    UserProfileView,
    CustomPasswordResetView,
    CustomPasswordResetDoneView,
    CustomPasswordResetConfirmView,
    CustomPasswordResetCompleteView,
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('signup/', CustomerSignupView.as_view(), name='signup'),

    # Staff & Customer Directories
    path('staff/', StaffListCreateView.as_view(), name='staff-list-create'),
    path('customers/', CustomerListView.as_view(), name='customer-list'),
    path('profile/', UserProfileView.as_view(), name='profile'),

    # Built-in Password Reset Flow
    path('password-reset/', CustomPasswordResetView.as_view(), name='password-reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password-reset-done'),
    path('password-reset/confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password-reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password-reset-complete'),
]
