from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Flat user shape expected by the Orbit client."""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'is_buddy',
            'verification_status', 'avatar_url', 'push_token',
        ]
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    full_name = serializers.CharField(required=True)
    is_buddy = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ['email', 'password', 'full_name', 'is_buddy']

    def create(self, validated_data):
        password = validated_data.pop('password')
        full_name = validated_data.get('full_name', '')
        is_buddy = validated_data.get('is_buddy', False)

        # Also populate first_name/last_name for admin compatibility.
        parts = full_name.split(' ', 1)
        validated_data['first_name'] = parts[0]
        validated_data['last_name'] = parts[1] if len(parts) > 1 else ''

        # Buddies start in pending verification.
        validated_data['verification_status'] = 'pending' if is_buddy else 'none'

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(style={'input_type': 'password'}, required=True)
    new_password = serializers.CharField(style={'input_type': 'password'}, required=True)
    confirm_password = serializers.CharField(style={'input_type': 'password'}, required=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': _("New passwords don't match")})
        user = self.context['request'].user
        if not user.check_password(data['current_password']):
            raise serializers.ValidationError({'current_password': _("Current password is incorrect")})
        return data


class PhoneVerificationSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)


class VerifyPhoneCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    verification_code = serializers.CharField(required=True)


class FirebaseAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True)


class PushTokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    platform = serializers.CharField(required=False, default='')
