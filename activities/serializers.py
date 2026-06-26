from rest_framework import serializers
from .models import Activity


class ActivitySerializer(serializers.ModelSerializer):
    # Expose host FK as host_id (the shape the client expects).
    host_id = serializers.PrimaryKeyRelatedField(source='host', read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False)

    class Meta:
        model = Activity
        fields = [
            'id', 'host_id', 'title', 'category', 'price',
            'latitude', 'longitude', 'scheduled_at', 'status',
            'created_at',
        ]
        read_only_fields = ['id', 'host_id', 'created_at']


class ActivityCreateSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, coerce_to_string=False, required=False, default=0)

    class Meta:
        model = Activity
        fields = ['title', 'category', 'price', 'latitude', 'longitude', 'scheduled_at', 'status']

    def create(self, validated_data):
        validated_data['host'] = self.context['request'].user
        return super().create(validated_data)
