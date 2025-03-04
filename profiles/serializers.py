from rest_framework import serializers
from .models import UserProfile, Interest, InterestChoice, Availability


class InterestChoiceSerializer(serializers.ModelSerializer):
    """Serializer for interest choices"""
    class Meta:
        model = InterestChoice
        fields = ['id', 'name']


class InterestSerializer(serializers.ModelSerializer):
    """Serializer for interests"""
    choices = InterestChoiceSerializer(many=True, read_only=True)
    
    class Meta:
        model = Interest
        fields = ['id', 'name', 'description', 'choices']


class AvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for availability"""
    day_name = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = Availability
        fields = ['id', 'day_of_week', 'day_name', 'start_time', 'end_time']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for user profile"""
    interests = InterestChoiceSerializer(many=True, read_only=True)
    availabilities = AvailabilitySerializer(many=True, read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'bio', 'birth_date', 'gender', 'profile_picture',
            'location', 'latitude', 'longitude', 'max_distance_preference',
            'interests', 'availabilities', 'is_profile_complete',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
