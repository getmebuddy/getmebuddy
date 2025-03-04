# In users/services.py
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class FirebaseAuthService:
    """Service for Firebase authentication"""
    
    def __init__(self):
        """Initialize Firebase admin SDK"""
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Initialize Firebase with service account credentials
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS)
            firebase_admin.initialize_app(cred)
    
    def verify_id_token(self, id_token):
        """Verify the Firebase ID token"""
        try:
            # Verify the token
            decoded_token = auth.verify_id_token(id_token)
            
            # Get user info
            uid = decoded_token['uid']
            email = decoded_token.get('email')
            email_verified = decoded_token.get('email_verified', False)
            display_name = decoded_token.get('name')
            photo_url = decoded_token.get('picture')
            
            # Determine sign-in provider
            provider_data = decoded_token.get('firebase', {}).get('sign_in_provider', '')
            
            if 'google' in provider_data:
                signup_method = User.SIGNUP_GOOGLE
            elif 'facebook' in provider_data:
                signup_method = User.SIGNUP_FACEBOOK
            elif 'apple' in provider_data:
                signup_method = User.SIGNUP_APPLE
            else:
                signup_method = User.SIGNUP_EMAIL
            
            # Split display name into first and last name
            if display_name:
                names = display_name.split(' ', 1)
                first_name = names[0]
                last_name = names[1] if len(names) > 1 else ''
            else:
                first_name = ''
                last_name = ''
            
            return {
                'uid': uid,
                'email': email,
                'email_verified': email_verified,
                'first_name': first_name,
                'last_name': last_name,
                'photo_url': photo_url,
                'signup_method': signup_method
            }
        except Exception as e:
            raise ValueError(f"Invalid Firebase ID token: {str(e)}")
    
    def get_or_create_user(self, id_token):
        """Get or create user from Firebase ID token"""
        user_info = self.verify_id_token(id_token)
        
        # Check if user exists
        user = User.objects.filter(firebase_uid=user_info['uid']).first()
        
        if not user and user_info['email']:
            # Try to find user by email
            user = User.objects.filter(email=user_info['email']).first()
        
        created = False
        
        if not user:
            # Create new user
            user = User.objects.create(
                email=user_info['email'],
                first_name=user_info['first_name'],
                last_name=user_info['last_name'],
                firebase_uid=user_info['uid'],
                signup_method=user_info['signup_method'],
                is_active=True
            )
            created = True
        elif not user.firebase_uid:
            # Update existing user with Firebase UID
            user.firebase_uid = user_info['uid']
            user.signup_method = user_info['signup_method']
            user.save(update_fields=['firebase_uid', 'signup_method'])
        
        return user, created