from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    PasswordChangeSerializer,
    PhoneVerificationSerializer,
    VerifyPhoneCodeSerializer,
    FirebaseAuthSerializer,
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for users
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Ensure users can only see their own record unless they're staff
        """
        user = self.request.user
        if user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=user.id)
    
    @action(detail=False, methods=['put'], serializer_class=PasswordChangeSerializer)
    def change_password(self, request):
        """
        Change password endpoint
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        
        return Response({"detail": _("Password changed successfully")})
    
    @action(detail=False, methods=['post'], serializer_class=PhoneVerificationSerializer, permission_classes=[permissions.IsAuthenticated])
    def request_phone_verification(self, request):
        """
        Request phone verification code
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In a real implementation, integrate with Twilio or similar SMS service
        # to send verification code
        
        # For this MVP, we'll simulate successful code sending
        return Response({
            "detail": _("Verification code sent successfully"),
            "phone_number": serializer.validated_data['phone_number']
        })
    
    @action(detail=False, methods=['post'], serializer_class=VerifyPhoneCodeSerializer, permission_classes=[permissions.IsAuthenticated])
    def verify_phone(self, request):
        """
        Verify phone number with code
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # In a real implementation, verify the code against what was sent
        
        # For this MVP, we'll simulate successful verification with code "123456"
        if serializer.validated_data['verification_code'] == "123456":
            user = request.user
            user.phone_number = serializer.validated_data['phone_number']
            user.is_phone_verified = True
            user.save()
            
            return Response({
                "detail": _("Phone number verified successfully"),
                "user": UserSerializer(user).data
            })
        
        return Response({
            "detail": _("Invalid verification code")
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # In users/views.py, update the firebase_auth action
    @action(detail=False, methods=['post'], serializer_class=FirebaseAuthSerializer, permission_classes=[permissions.AllowAny])
    def firebase_auth(self, request):
        """
        Authenticate with Firebase ID token
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        id_token = serializer.validated_data['id_token']
        
        try:
            # Initialize Firebase service
            firebase_service = FirebaseAuthService()
            
            # Get or create user from Firebase token
            user, created = firebase_service.get_or_create_user(id_token)
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data,
                'created': created
            })
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens for the new user
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
