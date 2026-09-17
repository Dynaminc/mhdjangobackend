# apps/users/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'), 
    path('check-email/', CheckEmailView.as_view(), name='check-email'),
    path('resend-verification/', ResendVerificationView.as_view(), name='resend-verification'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/confirm/', ResetPasswordConfirmView.as_view(), name='reset-password-confirm'),

    # Google authentication
    path('google-signup/', GoogleSignUpView.as_view(), name='google-signup'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
    # path(r'profiles',ProfileViewSet.as_view(), name='profile'), # ProfilesView.as_view()
    # ✅ Provide actions mapping
    path('profiles/', ProfileViewSet.as_view({
        'get': 'list',      # GET request -> list action
        'post': 'create',   # POST request -> create action
    }), name='profile-list'),
    
    path('profiles/<int:pk>/', ProfileViewSet.as_view({
        'get': 'retrieve',     # GET request -> retrieve action
        'put': 'update',       # PUT request -> update action
        'patch': 'partial_update',  # PATCH request -> partial_update action
        'delete': 'destroy',   # DELETE request -> destroy action
    }), name='profile-detail'),
    
    # Custom actions
    path('profiles/doctors/', ProfileViewSet.as_view({
        'get': 'get_doctors',  # GET request -> get_doctors action
    }), name='profile-doctors'),
    
    path('profiles/patients/', ProfileViewSet.as_view({
        'get': 'get_patients',
    }), name='profile-patients'),
    
    path('profiles/admins/', ProfileViewSet.as_view({
        'get': 'get_admins',
    }), name='profile-admins'),
    
    path('profiles/<int:pk>/full/', ProfileViewSet.as_view({
        'get': 'get_full_profile',
    }), name='profile-full'),
    
    path('profiles/<int:pk>/role/', ProfileViewSet.as_view({
        'patch': 'update_role',
    }), name='profile-role'),    
    path('profile/', CurrentUserProfileView.as_view(), name='current-profile'),
    
    # Initial Onboarding (Step 1)
    path('onboarding/initial/', InitialOnboardingView.as_view(), name='initial-onboarding'),
    path('onboarding/status/', CheckOnboardingStatusView.as_view(), name='onboarding-status'),
    
    # Main Onboarding (Step 2 - Patient/Doctor Profile)
    path('onboarding/main/', MainOnboardingView.as_view(), name='main-onboarding'),
    path('onboarding/main/get/', GetMainOnboardingView.as_view(), name='get-main-onboarding'),
    
]