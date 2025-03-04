import math
from datetime import datetime, timedelta
from django.db.models import Count, F, Q, Value
from django.db.models.functions import Greatest
from django.contrib.auth import get_user_model

from profiles.models import UserProfile, InterestChoice, Availability
from matching.models import Match, MatchPreference

User = get_user_model()

class MatchingService:
    """Service class for buddy matching algorithm"""
    
    def __init__(self, user):
        """Initialize with the user we want to find matches for"""
        self.user = user
        self.user_profile = UserProfile.objects.get(user=user)
        self.match_preferences = MatchPreference.objects.get_or_create(user=user)[0]
    
    def find_potential_matches(self, limit=20):
        """Find potential matches based on preferences"""
        # Get user's location
        user_lat = self.user_profile.latitude
        user_long = self.user_profile.longitude
        
        # Get all user interests
        user_interests = set(self.user_profile.interests.values_list('id', flat=True))
        
        # Get all availabilities for the user
        user_availabilities = self.user_profile.availabilities.all()
        
        # Base query - exclude self and already matched users
        queryset = UserProfile.objects.exclude(
            Q(user=self.user) | 
            Q(user__initiated_matches__responder=self.user) | 
            Q(user__received_matches__initiator=self.user)
        ).filter(
            is_profile_complete=True,
            user__is_active=True,
            user__is_suspended=False
        )
        
        # Filter by gender preferences if specified
        if self.match_preferences.preferred_genders:
            queryset = queryset.filter(gender__in=self.match_preferences.preferred_genders)
        
        # Filter by age range if birthdate is provided
        if self.user_profile.birth_date:
            min_birth_date = datetime.now().date() - timedelta(days=365 * self.match_preferences.max_age)
            max_birth_date = datetime.now().date() - timedelta(days=365 * self.match_preferences.min_age)
            queryset = queryset.filter(
                birth_date__gte=min_birth_date,
                birth_date__lte=max_birth_date
            )
        
        # Calculate and annotate scores for each potential match
        matches = []
        
        for profile in queryset:
            # Calculate interest similarity score
            profile_interests = set(profile.interests.values_list('id', flat=True))
            common_interests = user_interests.intersection(profile_interests)
            total_interests = user_interests.union(profile_interests)
            interest_score = len(common_interests) / max(len(total_interests), 1) * 100
            
            # Calculate distance score if location is available
            distance_score = 0
            if user_lat and user_long and profile.latitude and profile.longitude:
                distance = self._calculate_distance(
                    user_lat, user_long, profile.latitude, profile.longitude
                )
                # Convert distance to a score: 100 for 0km, 0 for max_distance_preference or more
                max_distance = self.user_profile.max_distance_preference
                distance_score = max(0, (max_distance - distance) / max_distance * 100)
            
            # Calculate availability compatibility score
            availability_score = 0
            profile_availabilities = profile.availabilities.all()
            if user_availabilities.exists() and profile_availabilities.exists():
                availability_score = self._calculate_availability_score(
                    user_availabilities, profile_availabilities
                )
            
            # Calculate total match score based on weights in preferences
            total_score = (
                interest_score * self.match_preferences.interest_importance +
                distance_score * self.match_preferences.distance_importance +
                availability_score * self.match_preferences.availability_importance
            )
            
            # Add to matches list with scores
            matches.append({
                'user': profile.user,
                'profile': profile,
                'interest_score': interest_score,
                'distance_score': distance_score,
                'availability_score': availability_score,
                'total_score': total_score
            })
        
        # Sort by total score and limit results
        matches.sort(key=lambda x: x['total_score'], reverse=True)
        return matches[:limit]
    
    def create_match(self, responder_id):
        """Create a match between users"""
        responder = User.objects.get(id=responder_id)
        
        # Check if a match already exists
        existing_match = Match.objects.filter(
            (Q(initiator=self.user) & Q(responder=responder)) |
            (Q(initiator=responder) & Q(responder=self.user))
        ).first()
        
        if existing_match:
            return existing_match
        
        # Get user profiles
        initiator_profile = self.user_profile
        responder_profile = UserProfile.objects.get(user=responder)
        
        # Calculate scores
        # Interest similarity
        initiator_interests = set(initiator_profile.interests.values_list('id', flat=True))
        responder_interests = set(responder_profile.interests.values_list('id', flat=True))
        common_interests = initiator_interests.intersection(responder_interests)
        total_interests = initiator_interests.union(responder_interests)
        interest_score = len(common_interests) / max(len(total_interests), 1) * 100
        
        # Distance score
        distance_score = 0
        if (initiator_profile.latitude and initiator_profile.longitude and 
            responder_profile.latitude and responder_profile.longitude):
            distance = self._calculate_distance(
                initiator_profile.latitude, initiator_profile.longitude,
                responder_profile.latitude, responder_profile.longitude
            )
            max_distance = initiator_profile.max_distance_preference
            distance_score = max(0, (max_distance - distance) / max_distance * 100)
        
        # Availability score
        initiator_availabilities = initiator_profile.availabilities.all()
        responder_availabilities = responder_profile.availabilities.all()
        availability_score = 0
        if initiator_availabilities.exists() and responder_availabilities.exists():
            availability_score = self._calculate_availability_score(
                initiator_availabilities, responder_availabilities
            )
        
        # Total score
        prefs = self.match_preferences
        total_score = (
            interest_score * prefs.interest_importance +
            distance_score * prefs.distance_importance +
            availability_score * prefs.availability_importance
        )
        
        # Create match with expiration date (7 days from now)
        expiration_date = datetime.now() + timedelta(days=7)
        
        match = Match.objects.create(
            initiator=self.user,
            responder=responder,
            interests_similarity_score=interest_score,
            distance_score=distance_score,
            availability_score=availability_score,
            total_match_score=total_score,
            expiration_date=expiration_date
        )
        
        return match
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in kilometers"""
        # Radius of Earth in kilometers
        R = 6371
        
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Difference between coordinates
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def _calculate_availability_score(self, user_availabilities, match_availabilities):
        """Calculate overlap in availability schedules"""
        total_overlap_minutes = 0
        
        for user_avail in user_availabilities:
            user_day = user_avail.day_of_week
            user_start = user_avail.start_time
            user_end = user_avail.end_time
            
            for match_avail in match_availabilities:
                # Check if same day
                if match_avail.day_of_week != user_day:
                    continue
                
                match_start = match_avail.start_time
                match_end = match_avail.end_time
                
                # Check for overlap
                if match_start <= user_end and match_end >= user_start:
                    # Calculate overlap in minutes
                    overlap_start = max(user_start, match_start)
                    overlap_end = min(user_end, match_end)
                    
                    # Convert time objects to minutes for calculation
                    start_minutes = overlap_start.hour * 60 + overlap_start.minute
                    end_minutes = overlap_end.hour * 60 + overlap_end.minute
                    
                    overlap_minutes = end_minutes - start_minutes
                    total_overlap_minutes += overlap_minutes
        
        # Score is based on total overlap time (max score for 10+ hours overlap per week)
        max_overlap_minutes = 10 * 60  # 10 hours in minutes
        availability_score = min(100, (total_overlap_minutes / max_overlap_minutes) * 100)
        
        return availability_score