import secrets
from datetime import timedelta
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('role', User.Role.CUSTOMER)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', User.Role.ADMIN)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Custom User model using email as unique identifier and built-in RBAC:
    - Admin: Full control over system, products, plans, taxes, discounts, staff
    - Staff: Day-to-day handling of quotes, subscriptions, and billing
    - Customer: Self-service access to own subscriptions and invoices
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrator')
        STAFF = 'staff', _('Internal Staff')
        CUSTOMER = 'customer', _('Customer')

    username = None
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
        help_text=_('Designates role-based access level.')
    )
    company_name = models.CharField(max_length=255, blank=True, help_text=_('Company or business name'))
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ['-date_joined']
        verbose_name = _('User')
        verbose_name_plural = _('Users')

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        if name and self.company_name:
            return f"{name} ({self.company_name}) - {self.email}"
        if name:
            return f"{name} ({self.email})"
        if self.company_name:
            return f"{self.company_name} ({self.email})"
        return self.email

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_staff_role(self):
        return self.role in [self.Role.ADMIN, self.Role.STAFF] or self.is_staff or self.is_superuser

    @property
    def is_customer_role(self):
        return self.role == self.Role.CUSTOMER

    def save(self, *args, **kwargs):
        # Automatically sync is_staff for admin and staff roles so they can access Django admin if needed
        if self.role in [self.Role.ADMIN, self.Role.STAFF]:
            self.is_staff = True
        if self.role == self.Role.ADMIN:
            self.is_superuser = True
        super().save(*args, **kwargs)


class PasswordResetToken(models.Model):
    """
    Secure password reset token for self-service forgotten password flow.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @classmethod
    def create_for_user(cls, user, expires_in_hours=24):
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        return cls.objects.create(user=user, token=token, expires_at=expires_at)

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

    def __str__(self):
        return f"Reset token for {self.user.email} (valid={self.is_valid()})"
