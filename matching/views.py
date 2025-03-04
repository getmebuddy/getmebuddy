# In matching/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from .models import Match, MatchPreference
from .serializers import MatchSerializer, MatchPreferenceSerializer
from .services import MatchingService
from profiles.serializers import UserProfileSerializer

User = get_user_model()

class MatchViewSet(viewsets.ModelViewSet):
    """API endpoint for matches"""
    queryset = Match.objects.all()
    serializer_class = MatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return matches for the current user"""
        user = self.request.user
        return Match.objects.filter(
            Q(initiator=user) | Q(responder=user)
        )
    
    @action(detail=False, methods=['get'])
    def potential_matches(self, request):
        """Get potential matches for the current user"""
        matching_service = MatchingService(request.user)
        potential_matches = matching_service.find_potential_matches()
        
        # Format the response
        data = [{
            'user_id': match['user'].id,
            'first_name': match['user'].first_name,
            'last_name': match['user'].last_name,
            'profile': UserProfileSerializer(match['profile']).data,
            'scores': {
                'interest_score': round(match['interest_score'], 2),
                'distance_score': round(match['distance_score'], 2),
                'availability_score': round(match['availability_score'], 2),
                'total_score': round(match['total_score'], 2),
            }
        } for match in potential_matches]
        
        return Response(data)
    
    @action(detail=False, methods=['post'])
    def create_match(self, request):
        """Create a match with another user"""
        responder_id = request.data.get('responder_id')
        
        if not responder_id:
            return Response(
                {'error': 'Responder ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            matching_service = MatchingService(request.user)
            match = matching_service.create_match(responder_id)
            
            return Response(
                MatchSerializer(match).data,
                status=status.HTTP_201_CREATED
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Respond to a match request"""
        response = request.data.get('response')
        
        if response not in ['accept', 'reject']:
            return Response(
                {'error': 'Response must be either "accept" or "reject"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        match = self.get_object()
        
        # Ensure the user is the responder
        if match.responder != request.user:
            return Response(
                {'error': 'You are not authorized to respond to this match'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Update match status
        if response == 'accept':
            match.status = Match.STATUS_ACCEPTED
        else:
            match.status = Match.STATUS_REJECTED
        
        match.save()
        return Response(MatchSerializer(match).data)

class MatchPreferenceViewSet(viewsets.ModelViewSet):
    """API endpoint for match preferences"""
    serializer_class = MatchPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Return match preferences for the current user"""
        return MatchPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create match preferences for the current user"""
        preferences, _ = MatchPreference.objects.get_or_create(user=self.request.user)
        return preferences