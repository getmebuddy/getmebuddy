# In matching/serializers.py
from rest_framework import serializers
from .models import Match, MatchPreference

class MatchSerializer(serializers.ModelSerializer):
    """Serializer for matches"""
    initiator_name = serializers.CharField(source='initiator.get_full_name', read_only=True)
    responder_name = serializers.CharField(source='responder.get_full_name', read_only=True)
    
    class Meta:
        model = Match
        fields = [
            'id', 'initiator', 'responder', 'initiator_name', 'responder_name',
            'status', 'matched_at', 'updated_at', 'expiration_date', 
            'interests_similarity_score', 'distance_score', 
            'availability_score', 'total_match_score'
        ]
        read_only_fields = [
            'id', 'initiator', 'responder', 'matched_at', 'updated_at',
            'interests_similarity_score', 'distance_score', 
            'availability_score', 'total_match_score'
        ]

class MatchPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for match preferences"""
    
    class Meta:
        model = MatchPreference
        fields = [
            'id', 'min_age', 'max_age', 'preferred_genders',
            'interest_importance', 'distance_importance', 'availability_importance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']