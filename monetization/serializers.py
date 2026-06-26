from rest_framework import serializers
from .models import Booking
from activities.serializers import ActivitySerializer


class BookingSerializer(serializers.ModelSerializer):
    activity_id = serializers.PrimaryKeyRelatedField(source='activity', read_only=True)
    # Nest the full activity so the client can show title/price without a second fetch.
    activity = ActivitySerializer(read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'activity_id', 'activity', 'status', 'payment_intent_id', 'created_at']
        read_only_fields = ['id', 'created_at', 'activity_id', 'activity']


class BookingCreateSerializer(serializers.ModelSerializer):
    activity_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Booking
        fields = ['activity_id', 'payment_intent_id', 'status']

    def validate_activity_id(self, value):
        from activities.models import Activity
        if not Activity.objects.filter(pk=value).exists():
            raise serializers.ValidationError('Activity not found.')
        return value

    def create(self, validated_data):
        from activities.models import Activity
        activity_id = validated_data.pop('activity_id')
        validated_data['activity'] = Activity.objects.get(pk=activity_id)
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
