from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import User, PasswordResetToken
from .validators import StrongPasswordValidator


class UserSerializer(serializers.ModelSerializer):
    """Public and internal representation of a User."""
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name',
            'role', 'company_name', 'phone', 'address',
            'date_joined', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'role', 'date_joined', 'created_at', 'updated_at']


class CustomerRegisterSerializer(serializers.ModelSerializer):
    """
    Self-service registration for new customers.
    Enforces unique email and strong password validation.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[StrongPasswordValidator()]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'company_name', 'phone', 'address'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        # Always enforce customer role for self-registration
        validated_data['role'] = User.Role.CUSTOMER
        user = User.objects.create_user(password=password, **validated_data)
        return user


class StaffCreateSerializer(serializers.ModelSerializer):
    """
    Staff creation serializer. Strictly executable only by System Admin.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[StrongPasswordValidator()]
    )

    class Meta:
        model = User
        fields = [
            'id', 'email', 'password', 'first_name',
            'last_name', 'company_name', 'phone'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['role'] = User.Role.STAFF
        user = User.objects.create_user(password=password, **validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """
    Authenticates user by email and password.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError("Both email and password are required.")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This user account is inactive.")

        attrs['user'] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Requests a password reset token for the given email.
    """
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email__iexact=value)
            return user
        except User.DoesNotExist:
            # We silently accept or return the user object to avoid email enumeration
            return None


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Resets user password using the provided reset token.
    """
    token = serializers.CharField()
    new_password = serializers.CharField(
        write_only=True,
        validators=[StrongPasswordValidator()]
    )
    confirm_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_new_password']:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})

        try:
            token_obj = PasswordResetToken.objects.get(token=attrs['token'])
            if not token_obj.is_valid():
                raise serializers.ValidationError({"token": "Password reset token is invalid or has expired."})
            attrs['token_obj'] = token_obj
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({"token": "Password reset token is invalid."})

        return attrs
