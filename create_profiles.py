from django.contrib.auth.models import User
from accounts.models import Profile, PatientProfile
import uuid

# Get the superuser
user = User.objects.get(username='dev')  # or email

# Create Profile
if not hasattr(user, 'profile'):
    profile = Profile.objects.create(
        user=user,
        mh_user_id=f"MH{str(uuid.uuid4().hex[:8]).upper()}",
        role='admin'
    )
    print(f"✅ Profile created for {user.email}")
else:
    profile = user.profile

# Create PatientProfile (optional for admin)
if not hasattr(profile, 'patient_profile'):
    PatientProfile.objects.create(profile=profile)
    print(f"✅ PatientProfile created for {user.email}")
    
# python manage.py shell --command="exec(open('create_profiles.py').read())"
