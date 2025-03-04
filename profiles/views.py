from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import UserProfile, Interest, InterestChoice, Availability
from .serializers import UserProfileSerializer, InterestSerializer, InterestChoiceSerializer, AvailabilitySerializer

# Views will be implemented here
