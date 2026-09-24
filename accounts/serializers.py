# apps/users/serializers.py
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from .models import Profile, PatientProfile, DoctorProfile
from referrals.models import SpecialistReferral    
import datetime


class RegisterSerializer(serializers.ModelSerializer):
    
    """
    Simplified registration - only email and password
    """
    
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    
    ref_id = serializers.CharField(
        write_only=True, required=False, allow_blank=True
    )
        
    class Meta:
        model = User
        fields = ('email', 'password', 'password2', 'ref_id')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        ref_id = validated_data.get('ref_id', None)
        email = validated_data['email']
        
        # Generate username from email (remove special chars)
        username = self.generate_username(email)
        validated_data['username'] = username
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data['password']
        )
        
        referral = None
        if ref_id:
            try:
                referral = SpecialistReferral.objects.get(reference_id=ref_id)
                if referral.linked_user:
                    return 'Exising', 402
                print(referral, 'referral here')
            except SpecialistReferral.DoesNotExist:
                referral = None

        if referral:
            # Only fill fields that the user didn't provide
            if not user.first_name and referral.first_name:
                user.first_name = referral.first_name
            if not user.last_name and referral.last_name:
                user.last_name = referral.last_name
            user.save(update_fields=['first_name', 'last_name'])
        # return user
    
    
        profile_defaults = {
            'mh_user_id': self.generate_mh_user_id(),
            'role': 'patient',
            'email_verified': bool(referral),
            'email_verified_at': datetime.datetime.now() if referral else None,
        }

        if referral:
            profile_defaults.update({
                'phone':   referral.phone or '',
                'age':     referral.age,
                'gender':  referral.sex or '',           # map sex → gender
                'country': referral.country or '',
                'state':   referral.state or '',
                'city':    referral.city or '',
                # date_of_birth not available — leave blank
            })
    
        # Create profile with auto-generated mh_user_id
        # mh_user_id=self.generate_mh_user_id()
        # profile = Profile.objects.create(
        #     user=user,
        #     mh_user_id=mh_user_id
            
        # )
        # PatientProfile.objects.create(profile=profile)
        profile = Profile.objects.create(user=user, **profile_defaults)
        print(profile, 'profile_created', profile_defaults)
        PatientProfile.objects.create(profile=profile)
        if referral and referral.linked_user_id is None:
            referral.linked_user = user
            referral.linked_at = datetime.datetime.now()
            referral.onboarding_complete = True
            referral.save(update_fields=[
                'linked_user', 'linked_at', 'onboarding_complete',
            ])

        return user, referral
    
    def generate_username(self, email):
        """Generate username from email"""
        username = email.split('@')[0]
        # Remove special characters
        username = ''.join(c for c in username if c.isalnum() or c == '_')
        
        # Ensure uniqueness
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username
    
    def generate_mh_user_id(self):
        """Generate a unique MHPro user ID"""
        import uuid
        year = datetime.datetime.now().year
        unique_part = uuid.uuid4().hex[:8].upper()
        return f"MH-{year}-{unique_part}"


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for User Profile with nested user info.
    """
    
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Profile
        fields = (
            'id',
            'mh_user_id',
            'user_id',
            'email',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'phone',
            'age',
            'gender',
            'date_of_birth',
            'bio',
            'profile_picture',
            'is_online',
            'language',
            'timezone',
            'notifications_enabled',
            'created_at',
            'updated_at'
        )
        read_only_fields = (
            'mh_user_id',
            'user_id',
            'email',
            'username',
            'created_at',
            'updated_at'
        )
    
    def get_full_name(self, obj):
        return obj.user.get_full_name()


# accounts/serializers.py

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'username']
  
  
class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    full_name = serializers.SerializerMethodField()
    is_doctor = serializers.SerializerMethodField()
    is_patient = serializers.SerializerMethodField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'id',
            'user',
            'mh_user_id',
            'role',
            'full_name',
            'is_doctor',
            'is_patient',
            'is_admin',
            'phone',
            'date_of_birth',
            'gender',
            'created_at',
            'updated_at',
        ]

        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]

    def get_full_name(self, obj):
        return obj.user.get_full_name()

    def get_is_doctor(self, obj):
        return obj.role == 'doctor'

    def get_is_patient(self, obj):
        return obj.role == 'patient'

    def get_is_admin(self, obj):
        return obj.role == 'admin'        
# class ProfileSerializer(serializers.ModelSerializer):
#     user = UserSerializer(read_only=True)
#     full_name = serializers.SerializerMethodField()
#     is_doctor = serializers.SerializerMethodField()
#     is_patient = serializers.SerializerMethodField()
#     is_admin = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Profile
#         fields = [
#             'id', 'user', 'mh_user_id', 'role', 
#             'full_name', 'is_doctor', 'is_patient', 'is_admin',
#              'phone',
#             'date_of_birth',
#             'gender',
#             'created_at', 'updated_at'
#         ]
#         read_only_fields = ['id', 'created_at', 'updated_at']
    
#     def to_representation(self, instance):
#         """Add computed fields manually"""
#         data = super().to_representation(instance)
        
#         # ✅ Add computed properties
#         data['full_name'] = instance.user.get_full_name()
#         data['is_doctor'] = instance.role == 'doctor'
#         data['is_patient'] = instance.role == 'patient'
#         data['is_admin'] = instance.role == 'admin'
        
#         return data
        
#     def get_full_name(self, obj):
#         return obj.user.get_full_name()
    
#     @property
#     def get_is_doctor(self):
        
#         return Profile.role == 'doctor'
    
#     @property
#     def get_is_patient(self):
        
#         return self.role == 'patient'
    
#     @property
#     def get_is_admin(self):
        
#         return self.role == 'admin'


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, help_text="User email address")
    password = serializers.CharField(required=True, help_text="User password", write_only=True)
    
    
    
class OnboardingSerializer(serializers.Serializer):
    """Initial onboarding serializer"""
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, max_length=20, allow_blank=True)
    country = serializers.CharField(required=False, max_length=100, allow_blank=True)
    state = serializers.CharField(required=False, max_length=100, allow_blank=True)
    city = serializers.CharField(required=False, max_length=100, allow_blank=True)
    role = serializers.ChoiceField(choices=['patient', 'doctor'], required=False)


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = '__all__'
        read_only_fields = ('id', 'profile', 'created_at', 'updated_at')


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = '__all__'
        read_only_fields = ('id', 'profile', 'rating', 'created_at', 'updated_at')
    
    
# accounts/serializers.py
from rest_framework import serializers
from .models import Profile, PatientProfile, DoctorProfile


class OnboardingSerializer(serializers.Serializer):
    """Initial onboarding serializer"""
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    phone = serializers.CharField(required=False, max_length=20, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.CharField(required=False, max_length=20, allow_blank=True)
    country = serializers.CharField(required=False, max_length=100, allow_blank=True)
    state = serializers.CharField(required=False, max_length=100, allow_blank=True)
    city = serializers.CharField(required=False, max_length=100, allow_blank=True)
    role = serializers.ChoiceField(choices=['patient', 'doctor'], required=False)


class PatientProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientProfile
        fields = '__all__'
        read_only_fields = ('id', 'profile', 'created_at', 'updated_at')


class DoctorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorProfile
        fields = '__all__'
        read_only_fields = ('id', 'profile', 'rating', 'created_at', 'updated_at')    