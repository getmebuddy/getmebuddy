
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for the User model"""
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone_number',
            'is_phone_verified', 'is_identity_verified', 'date_joined',
        ]
        read_only_fields = [
            'id', 'date_joined', 'is_phone_verified', 'is_identity_verified',
        ]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name',
            'password', 'password_confirm',
        ]
    
    def validate(self, data):
        """Validate that passwords match"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": _("Passwords don't match")})
        return data
    
    def create(self, validated_data):
        """Create and return a new user"""
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change"""
    current_password = serializers.CharField(
        style={'input_type': 'password'},
        required=True,
    )
    new_password = serializers.CharField(
        style={'input_type': 'password'},
        required=True,
    )
    confirm_password = serializers.CharField(
        style={'input_type': 'password'},
        required=True,
    )
    
    def validate(self, data):
        """Validate that new passwords match and current password is correct"""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError(
                {"confirm_password": _("New passwords don't match")}
            )
            
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError(
                {"current_password": _("Current password is incorrect")}
            )
        
        return data


class PhoneVerificationSerializer(serializers.Serializer):
    """Serializer for phone verification requests"""
    phone_number = serializers.CharField(required=True)


class VerifyPhoneCodeSerializer(serializers.Serializer):
    """Serializer for verifying phone verification code"""
    phone_number = serializers.CharField(required=True)
    verification_code = serializers.CharField(required=True)


class FirebaseAuthSerializer(serializers.Serializer):
    """Serializer for Firebase authentication"""
    id_token = serializers.CharField(required=True)