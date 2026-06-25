from rest_framework import serializers
from .models import BlockedUser, Report


class BlockedUserSerializer(serializers.ModelSerializer):
    blocked_id = serializers.IntegerField(source='blocked.id', read_only=True)

    class Meta:
        model = BlockedUser
        fields = ['blocked_id', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    target_user_id = serializers.IntegerField(
        source='target_user.id', read_only=True, allow_null=True
    )

    class Meta:
        model = Report
        fields = ['id', 'target_user_id', 'target_type', 'target_id', 'reason', 'details', 'status', 'created_at']
        read_only_fields = ['id', 'status', 'created_at', 'target_user_id']
