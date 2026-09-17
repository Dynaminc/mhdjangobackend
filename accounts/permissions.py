# apps/accounts/permissions.py
from rest_framework import permissions
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class IsPatient(BasePermission):
    """
    Allows access only to users with role='patient'.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'patient'
        return False


class IsDoctor(BasePermission):
    """
    Allows access only to users with role='doctor'.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'doctor'
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile') and request.user.profile.role == 'doctor':
            doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
            if doctor_profile:
                if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                    return True
                elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                    return True
                elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                    return True
        return False


class IsDoctorOrPatient(BasePermission):
    """
    Allows access to users with role='doctor' or role='patient'.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['doctor', 'patient']
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the doctor
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                        return True
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
                    elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                        return True
        
        return False


class IsDoctorOrPatientOrReadOnly(BasePermission):
    """
    Allows read-only access to all users, but write access only to doctors and patients.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['doctor', 'patient']
        return False
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the doctor
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
        
        return False


class IsDoctorOrReadOnly(BasePermission):
    """
    Allows read-only access to all users, but write access only to doctors.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'doctor'
        return False
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile') and request.user.profile.role == 'doctor':
            doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
            if doctor_profile:
                if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                    return True
                elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                    return True
                elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                    return True
        
        return False


class IsPatientOrReadOnly(BasePermission):
    """
    Allows read-only access to all users, but write access only to patients.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role == 'patient'
        return False
    
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile') and request.user.profile.role == 'patient':
            patient_profile = getattr(request.user.profile, 'patient_profile', None)
            if patient_profile:
                if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                    return True
                elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                    return True
                elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                    return True
        
        return False


class IsAppointmentParticipant(BasePermission):
    """
    Allows access to both the doctor and patient associated with the appointment.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the doctor
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                        return True
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
                    elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                        return True
        
        return False


class IsMedicalRecordOwner(BasePermission):
    """
    Allows access to the patient who owns the medical record and doctors who have consulted them.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
                    elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                        return True
            
            # Check if user is a doctor who has consulted this patient
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'patient_profile'):
                        # Check if doctor has consulted this patient
                        from consultations.models import Consultation
                        return Consultation.objects.filter(
                            patient_profile=obj.patient_profile,
                            doctor_profile=doctor_profile
                        ).exists()
                    elif hasattr(obj, 'patient'):
                        return obj.patient.consultations.filter(
                            doctor_profile=doctor_profile
                        ).exists()
                    elif hasattr(obj, 'patient_id'):
                        from accounts.models import PatientProfile
                        try:
                            patient = PatientProfile.objects.get(id=obj.patient_id)
                            return Consultation.objects.filter(
                                patient_profile=patient,
                                doctor_profile=doctor_profile
                            ).exists()
                        except PatientProfile.DoesNotExist:
                            return False
        
        return False


class IsLabOrderParticipant(BasePermission):
    """
    Allows access to the doctor who ordered the lab test and the patient it's for.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the ordering doctor
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                        return True
                    elif hasattr(obj, 'order') and hasattr(obj.order, 'doctor_profile'):
                        return obj.order.doctor_profile == doctor_profile
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
                    elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                        return True
                    elif hasattr(obj, 'order') and hasattr(obj.order, 'patient_profile'):
                        return obj.order.patient_profile == patient_profile
        
        return False


class IsPrescriptionParticipant(BasePermission):
    """
    Allows access to the doctor who prescribed and the patient it's for.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the prescribing doctor
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                        return True
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
                    elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                        return True
        
        return False


class IsConsultationParticipant(BasePermission):
    """
    Allows access to the doctor and patient involved in the consultation.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Check if user is the doctor
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor_id') and obj.doctor_id == doctor_profile.id:
                        return True
            
            # Check if user is the patient
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
                    elif hasattr(obj, 'patient_id') and obj.patient_id == patient_profile.id:
                        return True
        
        return False


class IsSelfOrDoctor(BasePermission):
    """
    Allows access to the user themselves or their doctor.
    """
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            # Check if user is accessing their own profile
            if hasattr(obj, 'profile') and hasattr(obj.profile, 'user') and obj.profile.user == request.user:
                return True
            if hasattr(obj, 'user') and obj.user == request.user:
                return True
            
            # Check if user is a doctor
            if request.user.profile.role == 'doctor':
                doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
                if doctor_profile:
                    # Doctor can access their patients' data
                    if hasattr(obj, 'patient_profile'):
                        from consultations.models import Consultation
                        return Consultation.objects.filter(
                            patient_profile=obj.patient_profile,
                            doctor_profile=doctor_profile
                        ).exists()
                    elif hasattr(obj, 'patient'):
                        return obj.patient.consultations.filter(
                            doctor_profile=doctor_profile
                        ).exists()
        
        return False


class HasProfilePermission(BasePermission):
    """
    Custom permission to check if user has a specific role.
    """
    def __init__(self, role):
        self.role = role
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            if self.role == 'doctor':
                return request.user.profile.role == 'doctor'
            elif self.role == 'patient':
                return request.user.profile.role == 'patient'
            elif self.role == 'admin':
                return request.user.is_staff
        
        return False


class CanManageAppointments(BasePermission):
    """
    Allows patients to manage their appointments and doctors to manage theirs.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['doctor', 'patient']
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Doctor can manage their appointments
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    elif hasattr(obj, 'doctor') and obj.doctor == doctor_profile:
                        return True
            
            # Patient can manage their appointments
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    elif hasattr(obj, 'patient') and obj.patient == patient_profile:
                        return True
        
        return False


class CanManageLabTests(BasePermission):
    """
    Allows doctors to manage lab tests and patients to view their own.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            return request.user.profile.role in ['doctor', 'patient']
        return False
    
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            
            # Doctor can manage all tests they ordered
            if profile.role == 'doctor':
                doctor_profile = getattr(profile, 'doctor_profile', None)
                if doctor_profile:
                    if hasattr(obj, 'doctor_profile') and obj.doctor_profile == doctor_profile:
                        return True
                    if hasattr(obj, 'order') and hasattr(obj.order, 'doctor_profile'):
                        return obj.order.doctor_profile == doctor_profile
            
            # Patient can view their own tests
            if profile.role == 'patient':
                patient_profile = getattr(profile, 'patient_profile', None)
                if patient_profile:
                    if hasattr(obj, 'patient_profile') and obj.patient_profile == patient_profile:
                        return True
                    if hasattr(obj, 'order') and hasattr(obj.order, 'patient_profile'):
                        return obj.order.patient_profile == patient_profile
        
        return False