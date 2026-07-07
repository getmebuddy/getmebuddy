from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Availability, Interest, InterestChoice, UserProfile
from .serializers import (
    AvailabilitySerializer,
    InterestChoiceSerializer,
    InterestSerializer,
    UserProfileSerializer,
)

# Views will be implemented here
