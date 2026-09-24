# apps/users/views.py
# apps/users/views.py
import uuid
import requests
import requests as http_requests
from datetime import datetime

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.tokens import default_token_generator
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile
from .serializers import *
from .tokens import email_verification_token

class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer
    queryset = User.objects.all()
    

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        
        referral = None
        user, referral = serializer.save()
        print('Referrealstatus',referral, user)
        # Build verification URL
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
            
        verify_url = (
            f"{settings.FRONTEND_URL}/verify-email"
            f"?uid={uid}&token={token}"
        )
        
        ref_id = serializer.validated_data['ref_id']
        print('Has ref id', ref_id)
        
        if not ref_id:
            # Send email
            send_mail(
                subject='Verify your MHPro account',
                message=(
                    f"Hi {user.first_name or user.email},\n\n"
                    f"Please verify your email by clicking the link below:\n\n"
                    f"{verify_url}\n\n"
                    f"If you didn't sign up, ignore this email."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            
        if ref_id:
            print("loggin in by refereeal")
            user.backend = settings.AUTHENTICATION_BACKENDS[0]
            login(request, user)
            
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'message': 'Account created. Check your email to verify.',
                'data': {
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'profile': {
                        'mh_user_id': user.profile.mh_user_id,
                        'role': user.profile.role,
                    },
                    'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                    },
                    'next_step': 'meet' if referral else 'verify_email',
                },
            }, status=status.HTTP_201_CREATED)
            
            # JWT tokens
    
        return Response({
            'status': 'success',
            'message': 'Account created. Check your email to verify.',
            'data': {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'profile': {
                    'mh_user_id': user.profile.mh_user_id,
                    'role': user.profile.role,
                },
                'next_step': 'meet' if referral else 'verify_email',
            },
        }, status=status.HTTP_201_CREATED)
        
class VerifyEmailView(APIView):
    """
    POST /api/v1/users/verify-email/
    Body: { "uid": "...", "token": "..." }

    Returns JSON. No redirects — the frontend handles the UI.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')

        if not uid or not token:
            return Response(
                {'status': 'error', 'message': 'Missing uid or token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decode uid → user
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {'status': 'error', 'message': 'Invalid verification link'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # # Validate token
        if not email_verification_token.check_token(user, token):
            return Response(
                {'status': 'error', 'message': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mark verified
        profile = user.profile
        if not profile.email_verified:
            profile.email_verified = True
            profile.email_verified_at = timezone.now()
            profile.save(update_fields=['email_verified', 'email_verified_at'])
            
            
        user.backend = settings.AUTHENTICATION_BACKENDS[0]
        login(request, user)
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'status': 'success',
            'message': 'Email verified successfully.',
            'data': {
                'email': user.email,
                'mh_user_id': profile.mh_user_id,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'profile': {
                    'user_id': user.profile.user_id,
                    'role': user.profile.role,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            },
        })
        
        
        
        
# class VerifyEmailView(APIView):
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         uid = request.data.get('uid')
#         token = request.data.get('token')

#         if not uid or not token:
#             return Response(
#                 {'status': 'error', 'message': 'Missing uid or token'},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         try:
#             user_id = force_str(urlsafe_base64_decode(uid))
#             user = User.objects.get(pk=user_id)
#         except (User.DoesNotExist, ValueError, TypeError):
#             return Response(
#                 {'status': 'error', 'message': 'Invalid verification link'},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         if not email_verification_token.check_token(user, token):
#             return Response(
#                 {'status': 'error', 'message': 'Invalid or expired token'},
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

#         # Mark verified
#         profile = user.profile
#         if not profile.email_verified:
#             profile.email_verified = True
#             profile.email_verified_at = timezone.now()
#             profile.save()

#         # If called from a browser, redirect to the frontend
#         frontend = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
#         return redirect(f'{frontend}/login?verified=1')
    
#     def ensure_profile(self, user):
#         """
#         Ensure the user has:
#           - Profile
#           - PatientProfile (since Google sign-ups default to patient)
#         Returns the Profile.
#         """
#         # ---- Profile ----
#         profile, _ = Profile.objects.get_or_create(
#             user=user,
#             defaults={
#                 'mh_user_id': self.generate_mh_user_id(),
#                 'role': 'patient',
#                 'email_verified': True,       # ✅ Google emails are pre-verified
#                 'signup_method': 'email',       # ✅
#             },
#         )

#         # ---- Role-specific subprofile ----
#         if profile.role == 'patient':
#             PatientProfile.objects.get_or_create(profile=profile)
#         elif profile.role == 'doctor':
#             DoctorProfile.objects.get_or_create(profile=profile)

#         return profile
                
# class RegisterView(generics.CreateAPIView):
#     """
#     Account creation - email and password only.
#     Auto-generates username and mh_user_id.
#     Upon creation, the user is automatically authenticated (session + JWT).
#     """
#     queryset = User.objects.all()
#     permission_classes = [permissions.AllowAny]
#     serializer_class = RegisterSerializer

#     def post(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         user = serializer.save()
        

#         # Generate JWT tokens for API consumption
#         refresh = RefreshToken.for_user(user)

#         return Response({
#             'status': 'success',
#             'message': 'Account created and authenticated successfully',
#             'data': {
#                 'user': {
#                     'id': user.id,
#                     'email': user.email,
#                     'username': user.username,
#                 },
#                 'profile': {
#                     'mh_user_id': user.profile.mh_user_id,
#                     'role': user.profile.role,  # Default: 'patient'
#                 },
#                 'tokens': {
#                     'refresh': str(refresh),
#                     'access': str(refresh.access_token),
#                 },
#                 'next_step': 'onboarding'  # Indicate user needs to complete profile
#             }
#         }, status=status.HTTP_201_CREATED)
        

class LoginView(APIView):
    """
    User login endpoint.
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='email',
                    description='User email address',
                    example='john@email.com'
                ),
                'password': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='password',
                    description='User password',
                    example='SecurePass123!'
                ),
            }
        ),
        responses={
            200: openapi.Response('Login successful'),
            400: openapi.Response('Bad request'),
            401: openapi.Response('Invalid credentials'),
        }
    )    
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        if not email or not password:
            return Response({
                'status': 'error',
                'message': 'Email and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Authenticate
        user = authenticate(username=user.username, password=password)
        
        if not user:
            return Response({
                'status': 'error',
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
                # ✅ Block unverified users (Google users are auto-verified)
        profile = getattr(user, 'profile', None)
        if user.is_superuser:
            def generate_mh_user_id():
                """Generate a unique MHPro user ID"""
                year = datetime.datetime.now().year
                unique_part = uuid.uuid4().hex[:8].upper()
                return f"MH-{year}-{unique_part}"
            if not profile:
                profile_defaults = {
                    'mh_user_id': generate_mh_user_id(),
                    'role': 'admin',
                    'email_verified': True,
                    'email_verified_at': datetime.datetime.now(),
                }
                    
                profile = Profile.objects.create(user=user, **profile_defaults)
                PatientProfile.objects.create(profile=profile)
            else:
                profile.role = 'admin'
                profile.save()
        if profile and profile.signup_method == 'email' and not profile.email_verified:
            return Response({
                'status': 'error',
                'message': 'Please verify your email before logging in.',
                'code': 'email_not_verified',
                'email': user.email,
            }, status=status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'status': 'success',
            'message': 'Login successful',
            'data': {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'profile': {
                    'user_id': user.profile.user_id,
                    'role': user.profile.role,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        })


# apps/accounts/views.py
class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't leak which emails exist
            return Response({'status': 'success', 'message': 'If that email exists, we sent a link.'})

        profile = user.profile
        if profile.email_verified:
            return Response({'status': 'success', 'message': 'Email already verified.'})

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        verify_url = request.build_absolute_uri(
            reverse('verify-email') + f'?uid={uid}&token={token}'
        )

        send_mail(
            subject='Verify your MHPro account',
            message=f"Click to verify: {verify_url}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        return Response({'status': 'success', 'message': 'Verification email sent.'})
    
class GoogleSignUpView(APIView):
    """
    Google Sign-Up / Login
    Handles both new-user registration and existing-user login via Google.

    Creates Profile + PatientProfile on first sign-up.
    Auto-heals existing users that have no PatientProfile yet.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        google_token = request.data.get('token')
        ref_id = request.data.get('ref_id', None)
        access_token = request.data.get('access_token')

        if not google_token: # and not access_token:
            print('not google toekn', google_token)
            return Response({
                'status': 'error',
                'message': 'Google token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            if access_token:
                user_info = self.get_user_info_from_access_token(access_token)
            else:
                user_info = self.verify_google_token(google_token)

            email = user_info.get('email')
            first_name = user_info.get('given_name', '')
            last_name = user_info.get('family_name', '')
            google_id = user_info.get('sub')
            picture = user_info.get('picture', '')

            if not email:
                return Response({
                    'status': 'error',
                    'message': 'Email not provided by Google'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get or create the user
            try:
                user = User.objects.get(email=email)
                is_new_user = False

                # Update name if missing
                if not user.first_name and first_name:
                    user.first_name = first_name
                if not user.last_name and last_name:
                    user.last_name = last_name
                user.save()

            except User.DoesNotExist:
                is_new_user = True
                user = self.create_user_from_google(email, first_name, last_name, google_id)

            # Ensure Profile + PatientProfile exist for every Google login
            profile = self.ensure_profile(user)

            # Log in for session auth
            user.backend = settings.AUTHENTICATION_BACKENDS[0]
            login(request, user)

            # JWT tokens
            refresh = RefreshToken.for_user(user)

            onboarding_complete = bool(user.first_name and user.last_name and profile.phone)

            return Response({
                'status': 'success',
                'message': 'Google sign-up successful' if is_new_user else 'Login successful',
                'data': {
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'profile': {
                        'mh_user_id': profile.mh_user_id,
                        'role': profile.role,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'is_new_user': is_new_user,
                    'onboarding_complete': onboarding_complete,
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            print('Error here ', e)
            return Response({
                'status': 'error',
                'message': f'Invalid Google token: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print('failed here', e)
            return Response({
                'status': 'error',
                'message': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # =====================================================
    # TOKEN VERIFICATION
    # =====================================================
    def verify_google_token(self, token):
        """Verify Google ID token"""
        try:
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer')
            return id_info
        except ValueError as e:
            raise ValueError(f'Invalid token: {str(e)}')

    def get_user_info_from_access_token(self, access_token):
        """Get user info from Google access token"""
        try:
            response = http_requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            return response.json()
        except http_requests.exceptions.RequestException as e:
            raise ValueError(f'Failed to get user info: {str(e)}')

    # =====================================================
    # USER + PROFILE CREATION
    # =====================================================
    def create_user_from_google(self, email, first_name, last_name, google_id):
        """Create a new user + Profile + PatientProfile from Google data"""
        username = self.generate_username(email)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
        )
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # ✅ Create Profile + PatientProfile
        self.ensure_profile(user)

        return user

    def ensure_profile(self, user):
        """
        Ensure the user has:
          - Profile
          - PatientProfile (since Google sign-ups default to patient)
        Returns the Profile.
        """
        # ---- Profile ----
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                'mh_user_id': self.generate_mh_user_id(),
                'role': 'patient',
                'email_verified': True,       # ✅ Google emails are pre-verified
                'signup_method': 'google',    # ✅
            },
        )

        if profile.signup_method == 'email' and not profile.email_verified:
            profile.email_verified = True
            profile.signup_method = 'google'   # optional — or keep 'email'
            profile.save()
            
        # ---- Role-specific subprofile ----
        if profile.role == 'patient':
            PatientProfile.objects.get_or_create(profile=profile)
        elif profile.role == 'doctor':
            DoctorProfile.objects.get_or_create(profile=profile)

        return profile
    
    def link_referral(self, ref_id, user, profile):
        from datetime import timedelta

        if not ref_id:
            return
        try:
            referral = SpecialistReferral.objects.get(reference_id=ref_id)
        except SpecialistReferral.DoesNotExist:
            return

        # Fill profile from referral — don't overwrite existing values
        if not profile.phone and referral.phone:
            profile.phone = referral.phone
        if not profile.age and referral.age:
            profile.age = referral.age
        if not profile.gender and referral.sex:
            profile.gender = referral.sex
        if not profile.country and referral.country:
            profile.country = referral.country
        if not profile.state and referral.state:
            profile.state = referral.state
        if not profile.city and referral.city:
            profile.city = referral.city

        # Referral users are pre-verified
        profile.save()

        # Link referral
        if referral.linked_user_id is None:
            referral.linked_user = user
            referral.linked_at = timezone.now()
            referral.onboarding_complete = True
            referral.save(update_fields=[
                'linked_user', 'linked_at', 'onboarding_complete',
            ])    

    # =====================================================
    # HELPERS
    # =====================================================
    def generate_username(self, email):
        """Generate a unique username from the email"""
        username = email.split('@')[0]
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        base_username = username or 'user'
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username

    def generate_mh_user_id(self):
        """Generate a unique MHPro user ID"""
        year = datetime.datetime.now().year
        unique_part = uuid.uuid4().hex[:8].upper()
        return f"MH-{year}-{unique_part}"
    
    
# class GoogleSignUpView(APIView):
#     """
#     Google Sign-Up / Login View
#     Handles both new user registration and existing user login via Google
#     """
#     permission_classes = [permissions.AllowAny]

#     def post(self, request):
#         # Get token from request
#         google_token = request.data.get('token')
#         access_token = request.data.get('access_token')
        
#         if not google_token and not access_token:
#             return Response({
#                 'status': 'error',
#                 'message': 'Google token is required'
#             }, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             # Verify Google token
#             if access_token:
#                 # If using access_token directly
#                 user_info = self.get_user_info_from_access_token(access_token)
#             else:
#                 # If using id_token
#                 user_info = self.verify_google_token(google_token)

#             # Get user data
#             email = user_info.get('email')
#             first_name = user_info.get('given_name', '')
#             last_name = user_info.get('family_name', '')
#             google_id = user_info.get('sub')
#             picture = user_info.get('picture', '')

#             if not email:
#                 return Response({
#                     'status': 'error',
#                     'message': 'Email not provided by Google'
#                 }, status=status.HTTP_400_BAD_REQUEST)

#             # Check if user exists
#             try:
#                 user = User.objects.get(email=email)
#                 # User exists - login
#                 is_new_user = False
                
#             except User.DoesNotExist:
#                 # Create new user
#                 is_new_user = True
#                 user = self.create_user_from_google(email, first_name, last_name, google_id)
                
#                 # Save Google profile picture if available
#                 if picture:
#                     # Save profile picture logic here if needed
#                     pass

#             # Generate JWT tokens
#             refresh = RefreshToken.for_user(user)
            
#             # Check if onboarding is complete
#             onboarding_complete = bool(user.first_name and user.last_name and user.profile.phone)

#             return Response({
#                 'status': 'success',
#                 'message': 'Google sign-up successful' if is_new_user else 'Login successful',
#                 'data': {
#                     'user': {
#                         'id': user.id,
#                         'email': user.email,
#                         'username': user.username,
#                         'first_name': user.first_name,
#                         'last_name': user.last_name,
#                     },
#                     'profile': {
#                         'mh_user_id': user.profile.mh_user_id,
#                         'role': user.profile.role,
#                     },
#                     'tokens': {
#                         'refresh': str(refresh),
#                         'access': str(refresh.access_token),
#                     },
#                     'is_new_user': is_new_user,
#                     'onboarding_complete': onboarding_complete
#                 }
#             }, status=status.HTTP_200_OK)

#         except ValueError as e:
#             return Response({
#                 'status': 'error',
#                 'message': f'Invalid Google token: {str(e)}'
#             }, status=status.HTTP_400_BAD_REQUEST)
        
#         except Exception as e:
#             return Response({
#                 'status': 'error',
#                 'message': f'Authentication failed: {str(e)}'
#             }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def verify_google_token(self, token):
#         """Verify Google ID token"""
#         try:
#             # Verify the token using Google's API
#             id_info = id_token.verify_oauth2_token(
#                 token,
#                 google_requests.Request(),
#                 settings.GOOGLE_CLIENT_ID
#             )
            
#             # Check if the token is valid
#             if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
#                 raise ValueError('Wrong issuer')
            
#             return id_info
            
#         except ValueError as e:
#             raise ValueError(f'Invalid token: {str(e)}')

#     def get_user_info_from_access_token(self, access_token):
#         """Get user info from Google access token"""
#         try:
#             response = requests.get(
#                 'https://www.googleapis.com/oauth2/v2/userinfo',
#                 headers={'Authorization': f'Bearer {access_token}'}
#             )
#             response.raise_for_status()
#             return response.json()
            
#         except requests.exceptions.RequestException as e:
#             raise ValueError(f'Failed to get user info: {str(e)}')

#     def create_user_from_google(self, email, first_name, last_name, google_id):
#         """Create a new user from Google data"""
#         # Generate username from email
#         username = self.generate_username(email)
        
#         # Create user
#         user = User.objects.create_user(
#             username=username,
#             email=email,
#             password=None  # No password for Google users
#         )
#         user.first_name = first_name
#         user.last_name = last_name
#         user.save()
        
#         # Create profile
#         Profile.objects.create(
#             user=user,
#             mh_user_id=self.generate_mh_user_id(user.id)
#         )
        
#         return user

#     def generate_username(self, email):
#         """Generate username from email"""
#         username = email.split('@')[0]
#         # Remove special characters
#         username = ''.join(c for c in username if c.isalnum() or c == '_')
        
#         # Ensure uniqueness
#         base_username = username
#         counter = 1
#         while User.objects.filter(username=username).exists():
#             username = f"{base_username}_{counter}"
#             counter += 1
#         return username


#     def generate_mh_user_id(self):
#         """Generate a unique MHPro user ID"""
#         import uuid
#         year = datetime.datetime.now().year
#         unique_part = uuid.uuid4().hex[:8].upper()
#         return f"MH-{year}-{unique_part}"


class GoogleLoginView(APIView):
    """
    Simplified Google Login - only for existing users
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        token = request.data.get('token')
        
        if not token:
            return Response({
                'status': 'error',
                'message': 'Google token is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Verify Google token
            id_info = id_token.verify_oauth2_token(
                token,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID
            )
            
            email = id_info.get('email')
            
            if not email:
                return Response({
                    'status': 'error',
                    'message': 'Email not provided by Google'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'User not found. Please sign up first.'
                }, status=status.HTTP_404_NOT_FOUND)

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'status': 'success',
                'message': 'Login successful',
                'data': {
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                    },
                    'profile': {
                        'mh_user_id': user.profile.mh_user_id,
                        'role': user.profile.role,
                    },
                    'tokens': {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                    },
                    'onboarding_complete': bool(user.first_name and user.last_name and user.profile.phone)
                }
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            return Response({
                'status': 'error',
                'message': f'Invalid Google token: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Authentication failed: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




from .serializers import UserProfileSerializer


class ProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user profiles.
    Supports filtering by role, searching, and ordering.
    """
    queryset = Profile.objects.all().select_related('user')
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Filtering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'mh_user_id']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'mh_user_id']
    ordering_fields = ['created_at', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        queryset = super().get_queryset()
        
        # If not staff, users can only see their own profile
        if not self.request.user.is_staff:
            return queryset.filter(user=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['get'], url_path='doctors')
    def get_doctors(self, request):
        """Return ALL doctors (ignores current user's self-only filter)."""
        doctors = Profile.objects.filter(role='doctor')   # ✅ Use the manager directly
        serializer = self.get_serializer(doctors, many=True)
        return Response({
            'status': 'success',
            'count': doctors.count(),
            'data': serializer.data
        })

    
    @action(detail=False, methods=['get'], url_path='patients')
    def get_patients(self, request):
        """✅ Get ALL patient profiles (not just current user)"""
        # ✅ Use the model manager directly, NOT self.get_queryset()
        patients = Profile.objects.filter(role='patient')
        print('Patients found:', patients.count())  # Should show > 0
        serializer = self.get_serializer(patients, many=True)
        return Response({
            'status': 'success',
            'count': patients.count(),
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='admins')
    def get_admins(self, request):
        """Get all admin profiles"""
        admins = self.get_queryset().filter(role='admin')
        serializer = self.get_serializer(admins, many=True)
        return Response({
            'status': 'success',
            'count': admins.count(),
            'data': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='full')
    def get_full_profile(self, request, pk=None):
        """Get complete profile with related data"""
        profile = self.get_object()
        
        # Get related data based on role
        data = {
            'profile': self.get_serializer(profile).data,
        }
        
        if profile.role == 'doctor' and hasattr(profile, 'doctor_profile'):
            from .serializers import DoctorProfileSerializer
            data['doctor_details'] = DoctorProfileSerializer(profile.doctor_profile).data
        elif profile.role == 'patient' and hasattr(profile, 'patient_profile'):
            from .serializers import PatientProfileSerializer
            data['patient_details'] = PatientProfileSerializer(profile.patient_profile).data
        
        return Response({
            'status': 'success',
            'data': data
        })
    
    @action(detail=True, methods=['patch'], url_path='role')
    def update_role(self, request, pk=None):
        """Update user role (admin only)"""
        if not request.user.is_staff:
            return Response({
                'status': 'error',
                'message': 'Only admins can update roles'
            }, status=status.HTTP_403_FORBIDDEN)
        
        profile = self.get_object()
        new_role = request.data.get('role')
        
        if new_role not in ['patient', 'doctor', 'admin']:
            return Response({
                'status': 'error',
                'message': 'Invalid role. Must be patient, doctor, or admin'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile.role = new_role
        profile.save()
        
        return Response({
            'status': 'success',
            'message': f'Role updated to {new_role}',
            'data': self.get_serializer(profile).data
        })
        
class ProfilesView(APIView):
    """
    Get all user profiles (Admin only) or current user profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Check if user is admin/staff to see all profiles
        if request.user.is_staff or request.user.is_superuser:
            # Admin: return all profiles
            profiles = Profile.objects.all().select_related('user')
            serializer = UserProfileSerializer(profiles, many=True)
            return Response({
                'status': 'success',
                'count': profiles.count(),
                'data': serializer.data
            })
        else:
            # Regular user: return only their own profile
            try:
                profile = request.user.profile
                serializer = UserProfileSerializer(profile)
                return Response({
                    'status': 'success',
                    'data': serializer.data
                })
            except Profile.DoesNotExist:
                return Response({
                    'status': 'error',
                    'message': 'Profile not found for this user'
                }, status=status.HTTP_404_NOT_FOUND)

# =====================================================
# REQUEST PASSWORD RESET
# =====================================================
class ForgotPasswordView(APIView):
    """
    POST /api/v1/users/forgot-password/
    Body: { "email": "user@example.com" }

    Always returns 200 — never leaks whether the email exists.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')

        if not email:
            return Response(
                {'status': 'error', 'message': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not leak — respond success anyway
            return Response({
                'status': 'success',
                'message': 'If that email exists, a reset link has been sent.',
            })

        # Google users have no password — tell them to use Google
        profile = getattr(user, 'profile', None)
        if profile and profile.signup_method == 'google' and not user.has_usable_password():
            return Response({
                'status': 'error',
                'message': 'This account uses Google sign-in. Please log in with Google.',
            }, status=status.HTTP_400_BAD_REQUEST)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password"
            f"?uid={uid}&token={token}"
        )

        send_mail(
            subject='Reset your MHPro password',
            message=(
                f"Hi {user.first_name or user.email},\n\n"
                f"Click the link below to reset your password:\n\n"
                f"{reset_url}\n\n"
                f"If you didn't request this, ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            'status': 'success',
            'message': 'If that email exists, a reset link has been sent.',
        })


# =====================================================
# CONFIRM PASSWORD RESET
# =====================================================
class ResetPasswordConfirmView(APIView):
    """
    POST /api/v1/users/reset-password/confirm/
    Body: { "uid": "...", "token": "...", "new_password": "..." }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uid or not token or not new_password:
            return Response({
                'status': 'error',
                'message': 'uid, token and new_password are required',
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({
                'status': 'error',
                'message': 'Password must be at least 8 characters',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Decode uid
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({
                'status': 'error',
                'message': 'Invalid reset link',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate token
        if not default_token_generator.check_token(user, token):
            return Response({
                'status': 'error',
                'message': 'Invalid or expired reset link',
            }, status=status.HTTP_400_BAD_REQUEST)

        # Set the new password
        user.set_password(new_password)
        user.save()

        return Response({
            'status': 'success',
            'message': 'Password reset successfully. You can now log in.',
        })


class CurrentUserProfileView(APIView):
    """
    Get the current authenticated user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.profile
            data = UserProfileSerializer(profile).data
            if profile.role == 'patient' and hasattr(profile, 'patient_profile'):
                from .serializers import PatientProfileSerializer
                data['patient_profile'] = PatientProfileSerializer(profile.patient_profile).data
                return Response({
                    'status': 'success',
                    'data': data
                })
            return Response({
                'status': 'success',
                'data': data
            })
        except Profile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class CheckEmailView(APIView):
    """
    Check if email already exists.
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({
                'status': 'error',
                'message': 'Email is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        exists = User.objects.filter(email=email).exists()
        return Response({
            'status': 'success',
            'data': {
                'email': email,
                'exists': exists,
                'message': 'Email already registered' if exists else 'Email available'
            }
        })        
        
        
class InitialOnboardingView(APIView):
    """
    Initial onboarding - updates User first_name, last_name and Profile fields.
    This is the first step after account creation.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['first_name', 'last_name'],
            properties={
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                'phone': openapi.Schema(type=openapi.TYPE_STRING, description='Phone number'),
                'date_of_birth': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Date of birth (YYYY-MM-DD)'),
                'gender': openapi.Schema(type=openapi.TYPE_STRING, description='Gender (Male/Female/Other)'),
                'country': openapi.Schema(type=openapi.TYPE_STRING, description='Country'),
                'state': openapi.Schema(type=openapi.TYPE_STRING, description='State/Province'),
                'city': openapi.Schema(type=openapi.TYPE_STRING, description='City'),
                'role': openapi.Schema(type=openapi.TYPE_STRING, description='Role (patient/doctor)'),
            }
        ),
        responses={
            200: openapi.Response('Onboarding completed'),
            400: openapi.Response('Validation error'),
        }
    )
    def post(self, request):
        user = request.user
        data = request.data
        
        # Update User fields
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        if not first_name or not last_name:
            return Response({
                'status': 'error',
                'message': 'First name and last name are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        user.first_name = first_name
        user.last_name = last_name
        user.save()
        
        # Update Profile fields
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Update profile fields
        profile.phone = data.get('phone', profile.phone)
        profile.gender = data.get('gender', profile.gender)
        # Parse date_of_birth from string to date
        dob_str = data.get('date_of_birth')
        if dob_str:
            try:
                # Try parsing as YYYY-MM-DD
                profile.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                try:
                    # Try parsing as MM/DD/YYYY
                    profile.date_of_birth = datetime.strptime(dob_str, '%m/%d/%Y').date()
                except ValueError:
                    try:
                        # Try parsing as DD/MM/YYYY
                        profile.date_of_birth = datetime.strptime(dob_str, '%d/%m/%Y').date()
                    except ValueError:
                        return Response({
                            'status': 'error',
                            'message': 'Invalid date format. Use YYYY-MM-DD'
                        }, status=status.HTTP_400_BAD_REQUEST)
    
        # Update location fields (you'll need to add these to Profile model)
        profile.country = data.get('country', getattr(profile, 'country', ''))
        profile.state = data.get('state', getattr(profile, 'state', ''))
        profile.city = data.get('city', getattr(profile, 'city', ''))
        
        # Update role if provided
        role = data.get('role', 'patient')
        if role in ['patient', 'doctor', 'admin']:
            profile.role = role
        
        profile.save()
        
        # Calculate age from date_of_birth
        age = None
        if profile.date_of_birth:
            from datetime import date
            today = date.today()
            age = today.year - profile.date_of_birth.year
            if today.month < profile.date_of_birth.month or \
               (today.month == profile.date_of_birth.month and today.day < profile.date_of_birth.day):
                age -= 1
            profile.age = age
            profile.save()
        
        # Check if onboarding is complete
        onboarding_complete = bool(
            user.first_name and user.last_name and 
            profile.phone and profile.date_of_birth and profile.gender
        )
        
        return Response({
            'status': 'success',
            'message': 'Onboarding completed successfully',
            'data': {
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'profile': {
                    'mh_user_id': profile.mh_user_id,
                    'role': profile.role,
                    'phone': profile.phone,
                    'age': profile.age,
                    'gender': profile.gender,
                    'date_of_birth': profile.date_of_birth,
                    'country': getattr(profile, 'country', ''),
                    'state': getattr(profile, 'state', ''),
                    'city': getattr(profile, 'city', ''),
                },
                'onboarding_complete': onboarding_complete
            }
        })


class CheckOnboardingStatusView(APIView):
    """
    Check if user has completed onboarding.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        onboarding_complete = bool(
            user.first_name and user.last_name and 
            profile.phone and profile.country and profile.gender
        )
        
        return Response({
            'status': 'success',
            'data': {
                'onboarding_complete': onboarding_complete,
                'profile': {
                    'mh_user_id': profile.mh_user_id,
                    'role': profile.role,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'phone': profile.phone,
                    'age': profile.age,
                    'gender': profile.gender,
                    'date_of_birth': profile.date_of_birth,
                }
            }
        })


# accounts/views.py
class MainOnboardingView(APIView):
    """
    Main onboarding - updates PatientProfile or DoctorProfile.
    This is the second step after initial onboarding.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                # Patient fields
                'blood_type': openapi.Schema(type=openapi.TYPE_STRING, description='Blood type (A+, A-, B+, B-, AB+, AB-, O+, O-)'),
                'emergency_contact_name': openapi.Schema(type=openapi.TYPE_STRING, description='Emergency contact name'),
                'emergency_contact_phone': openapi.Schema(type=openapi.TYPE_STRING, description='Emergency contact phone'),
                'emergency_contact_relation': openapi.Schema(type=openapi.TYPE_STRING, description='Emergency contact relation'),
                'insurance_provider': openapi.Schema(type=openapi.TYPE_STRING, description='Insurance provider'),
                'insurance_number': openapi.Schema(type=openapi.TYPE_STRING, description='Insurance number'),
                'insurance_expiry': openapi.Schema(type=openapi.TYPE_STRING, format='date', description='Insurance expiry date'),
                'primary_care_physician': openapi.Schema(type=openapi.TYPE_STRING, description='Primary care physician'),
                
                # Doctor fields
                'specialty': openapi.Schema(type=openapi.TYPE_STRING, description='Medical specialty'),
                'license_number': openapi.Schema(type=openapi.TYPE_STRING, description='License number'),
                'years_experience': openapi.Schema(type=openapi.TYPE_INTEGER, description='Years of experience'),
                'consultation_fee': openapi.Schema(type=openapi.TYPE_NUMBER, description='Consultation fee'),
                'hospital_affiliation': openapi.Schema(type=openapi.TYPE_STRING, description='Hospital affiliation'),
                'bio': openapi.Schema(type=openapi.TYPE_STRING, description='Professional bio'),
                'education': openapi.Schema(type=openapi.TYPE_STRING, description='Education'),
                'certifications': openapi.Schema(type=openapi.TYPE_STRING, description='Certifications'),
            }
        ),
        responses={
            200: openapi.Response('Main onboarding completed'),
            400: openapi.Response('Validation error'),
        }
    )
    def post(self, request):
        user = request.user
        
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = request.data
        
        # Handle Patient Profile
        if profile.role == 'patient':
            patient_profile, created = PatientProfile.objects.get_or_create(profile=profile)
            
            # Update patient fields
            patient_profile.blood_type = data.get('blood_type', patient_profile.blood_type)
            patient_profile.emergency_contact_name = data.get('emergency_contact_name', patient_profile.emergency_contact_name)
            patient_profile.emergency_contact_phone = data.get('emergency_contact_phone', patient_profile.emergency_contact_phone)
            patient_profile.emergency_contact_relation = data.get('emergency_contact_relation', patient_profile.emergency_contact_relation)
            patient_profile.insurance_provider = data.get('insurance_provider', patient_profile.insurance_provider)
            patient_profile.insurance_number = data.get('insurance_number', patient_profile.insurance_number)
            patient_profile.insurance_expiry = data.get('insurance_expiry', patient_profile.insurance_expiry)
            patient_profile.primary_care_physician = data.get('primary_care_physician', patient_profile.primary_care_physician)
            patient_profile.save()
            
            return Response({
                'status': 'success',
                'message': 'Patient profile updated successfully',
                'data': {
                    'profile_type': 'patient',
                    'patient_profile': {
                        'blood_type': patient_profile.blood_type,
                        'emergency_contact_name': patient_profile.emergency_contact_name,
                        'emergency_contact_phone': patient_profile.emergency_contact_phone,
                        'emergency_contact_relation': patient_profile.emergency_contact_relation,
                        'insurance_provider': patient_profile.insurance_provider,
                        'insurance_number': patient_profile.insurance_number,
                        'insurance_expiry': patient_profile.insurance_expiry,
                        'primary_care_physician': patient_profile.primary_care_physician,
                    }
                }
            })
        
        # Handle Doctor Profile
        elif profile.role == 'doctor':
            doctor_profile, created = DoctorProfile.objects.get_or_create(profile=profile)
            
            # Update doctor fields
            doctor_profile.specialty = data.get('specialty', doctor_profile.specialty)
            doctor_profile.license_number = data.get('license_number', doctor_profile.license_number)
            doctor_profile.years_experience = data.get('years_experience', doctor_profile.years_experience)
            doctor_profile.consultation_fee = data.get('consultation_fee', doctor_profile.consultation_fee)
            doctor_profile.hospital_affiliation = data.get('hospital_affiliation', doctor_profile.hospital_affiliation)
            doctor_profile.bio = data.get('bio', doctor_profile.bio)
            doctor_profile.education = data.get('education', doctor_profile.education)
            doctor_profile.certifications = data.get('certifications', doctor_profile.certifications)
            doctor_profile.save()
            
            return Response({
                'status': 'success',
                'message': 'Doctor profile updated successfully',
                'data': {
                    'profile_type': 'doctor',
                    'doctor_profile': {
                        'specialty': doctor_profile.specialty,
                        'license_number': doctor_profile.license_number,
                        'years_experience': doctor_profile.years_experience,
                        'consultation_fee': str(doctor_profile.consultation_fee),
                        'hospital_affiliation': doctor_profile.hospital_affiliation,
                        'bio': doctor_profile.bio,
                        'education': doctor_profile.education,
                        'certifications': doctor_profile.certifications,
                    }
                }
            })
        
        return Response({
            'status': 'error',
            'message': 'Invalid role'
        }, status=status.HTTP_400_BAD_REQUEST)


class GetMainOnboardingView(APIView):
    """
    Get current user's main onboarding data (PatientProfile or DoctorProfile).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        try:
            profile = user.profile
        except Profile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Profile not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = {
            'role': profile.role,
            'initial_onboarding_complete': bool(
                user.first_name and user.last_name and 
                profile.phone and profile.date_of_birth and profile.gender
            )
        }
        
        if profile.role == 'patient':
            try:
                patient_profile = PatientProfile.objects.get(profile=profile)
                data['patient_profile'] = {
                    'blood_type': patient_profile.blood_type,
                    'emergency_contact_name': patient_profile.emergency_contact_name,
                    'emergency_contact_phone': patient_profile.emergency_contact_phone,
                    'emergency_contact_relation': patient_profile.emergency_contact_relation,
                    'insurance_provider': patient_profile.insurance_provider,
                    'insurance_number': patient_profile.insurance_number,
                    'insurance_expiry': patient_profile.insurance_expiry,
                    'primary_care_physician': patient_profile.primary_care_physician,
                }
                data['main_onboarding_complete'] = bool(
                    patient_profile.emergency_contact_name and 
                    patient_profile.emergency_contact_phone
                )
            except PatientProfile.DoesNotExist:
                data['patient_profile'] = None
                data['main_onboarding_complete'] = False
        
        elif profile.role == 'doctor':
            try:
                doctor_profile = DoctorProfile.objects.get(profile=profile)
                data['doctor_profile'] = {
                    'specialty': doctor_profile.specialty,
                    'license_number': doctor_profile.license_number,
                    'years_experience': doctor_profile.years_experience,
                    'consultation_fee': str(doctor_profile.consultation_fee),
                    'hospital_affiliation': doctor_profile.hospital_affiliation,
                    'bio': doctor_profile.bio,
                    'education': doctor_profile.education,
                    'certifications': doctor_profile.certifications,
                }
                data['main_onboarding_complete'] = bool(
                    doctor_profile.specialty and 
                    doctor_profile.license_number
                )
            except DoctorProfile.DoesNotExist:
                data['doctor_profile'] = None
                data['main_onboarding_complete'] = False
        
        return Response({
            'status': 'success',
            'data': data
        })
        
        
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import json

User = get_user_model()

@csrf_exempt
def google_auth(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    body = json.loads(request.body)
    token = body.get('id_token')
    if not token:
        return JsonResponse({'error': 'id_token required'}, status=400)

    try:
        # Verify token with Google
        info = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            os.getenv('GOOGLE_CLIENT_ID'),
        )
    except ValueError as e:
        return JsonResponse({'error': f'Invalid token: {e}'}, status=401)

    email = info['email']
    name = info.get('name', '')

    user, created = User.objects.get_or_create(
        email=email,
        defaults={'username': email, 'first_name': name},
    )

    # Issue your own token — pick whichever auth you already use
    from rest_framework.authtoken.models import Token  # if you use DRF tokens
    token_obj, _ = Token.objects.get_or_create(user=user)

    return JsonResponse({
        'token': token_obj.key,
        'is_new': created,
        'user': {'id': user.id, 'email': user.email, 'name': user.first_name},
    })        