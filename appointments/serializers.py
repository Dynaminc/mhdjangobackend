# apps/appointments/serializers.py
from rest_framework import serializers
from django.utils import timezone
from .models import Clinic, Appointment, QueueEntry, DoctorAvailability
from accounts.models import PatientProfile, DoctorProfile


class ClinicSerializer(serializers.ModelSerializer):
    """Serializer for Clinic model"""
    
    doctor_count = serializers.IntegerField(read_only=True)
    has_multiple_doctors = serializers.BooleanField(read_only=True)
    available_doctors_count = serializers.IntegerField(
        source='available_doctors.count',
        read_only=True
    )
    
    class Meta:
        model = Clinic
        fields = [
            'id', 'name', 'address', 'phone', 'email',
            'doctors', 'is_active', 'appointment_duration',
            'allow_online_booking', 'requires_doctor_selection',
            'doctor_count', 'has_multiple_doctors', 'available_doctors_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')


class ClinicWithDoctorsSerializer(ClinicSerializer):
    """Clinic serializer with doctor details"""
    
    doctors = serializers.SerializerMethodField()
    
    class Meta(ClinicSerializer.Meta):
        fields = ClinicSerializer.Meta.fields + ['doctors']
    
    def get_doctors(self, obj):
        from accounts.serializers import DoctorProfileSerializer
        # Return only available doctors
        available_doctors = obj.available_doctors
        return DoctorProfileSerializer(available_doctors, many=True).data


class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for DoctorAvailability model"""
    
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    doctor_name = serializers.SerializerMethodField()
    is_break_time = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DoctorAvailability
        fields = [
            'id', 'doctor_profile', 'doctor_name',
            'day_of_week', 'day_display', 'start_time', 'end_time',
            'is_available', 'specific_date', 'break_start', 'break_end',
            'is_break_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    is_doctor_assigned = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    appointment_display = serializers.CharField(read_only=True)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient_profile', 'patient_name',
            'doctor_profile', 'doctor_name',
            'clinic', 'clinic_name',
            'appointment_date', 'start_time', 'end_time',
            'type', 'type_display', 'status', 'status_display',
            'reason', 'notes',
            'is_doctor_assigned', 'is_active',
            'doctor_assigned_at', 'doctor_assigned_by',
            'appointment_display', 'created_at', 'updated_at'
        ]
        read_only_fields = (
            'id', 'doctor_assigned_at', 'doctor_assigned_by',
            'created_at', 'updated_at'
        )
    
    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()
    
    def get_doctor_name(self, obj):
        if obj.doctor_profile:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        return "Unassigned"


class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'patient_profile',
            'clinic',
            'appointment_date',
            'start_time',
            'end_time',
            'type',
            'reason',
            'notes',
            'doctor_profile',
        ]
        extra_kwargs = {
            'doctor_profile': {'required': False, 'allow_null': True},
            # ✅ Remove read_only from patient_profile so frontend can send it
            'patient_profile': {'required': True},
        }

    def validate(self, data):
        clinic = data.get('clinic')
        doctor_profile = data.get('doctor_profile')
        appointment_date = data.get('appointment_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        # Validate date/time
        if appointment_date and start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })

        # Check if clinic requires doctor selection
        if clinic and clinic.requires_doctor_selection:
            if not doctor_profile:
                raise serializers.ValidationError({
                    'doctor_profile': 'This clinic requires you to select a doctor'
                })

            # Verify doctor belongs to this clinic
            if doctor_profile and doctor_profile not in clinic.doctors.all():
                raise serializers.ValidationError({
                    'doctor_profile': 'Selected doctor does not work at this clinic'
                })
        else:
            # If doctor is provided but doesn't belong to clinic, raise error
            if doctor_profile and clinic and doctor_profile not in clinic.doctors.all():
                raise serializers.ValidationError({
                    'doctor_profile': 'Selected doctor does not work at this clinic'
                })

        # Check for conflicting appointments
        if doctor_profile and appointment_date and start_time and end_time:
            conflicting = Appointment.objects.filter(
                doctor_profile=doctor_profile,
                appointment_date=appointment_date,
                start_time__lt=end_time,
                end_time__gt=start_time,
                status__in=['scheduled', 'confirmed', 'in_progress']
            )
            if self.instance:
                conflicting = conflicting.exclude(id=self.instance.id)

            if conflicting.exists():
                raise serializers.ValidationError({
                    'appointment_date': 'Doctor already has an appointment at this time'
                })

        return data

    def create(self, validated_data):
        """Create appointment with optional doctor assignment"""
        from .utils import auto_assign_doctor

        patient_profile = validated_data.get('patient_profile')
        clinic = validated_data.get('clinic')
        doctor_profile = validated_data.get('doctor_profile', None)

        # If no doctor assigned and clinic allows auto-assignment
        if not doctor_profile and clinic and not clinic.requires_doctor_selection:
            # Auto-assign the first available doctor
            doctor_profile = auto_assign_doctor(clinic, validated_data)

        # Create appointment
        appointment = Appointment.objects.create(
            patient_profile=patient_profile,
            clinic=clinic,
            doctor_profile=doctor_profile,
            appointment_date=validated_data.get('appointment_date'),
            start_time=validated_data.get('start_time'),
            end_time=validated_data.get('end_time'),
            type=validated_data.get('type', 'physical'),
            reason=validated_data.get('reason', ''),
            notes=validated_data.get('notes', ''),
            status='scheduled'
        )

        # If doctor was auto-assigned, log it
        if doctor_profile and not validated_data.get('doctor_profile'):
            appointment.doctor_assigned_at = timezone.now()
            appointment.save()

        return appointment


# utils.py
def auto_assign_doctor(clinic, appointment_data):
    """Auto-assign the first available doctor at the clinic"""
    try:
        # Get all doctors at this clinic
        doctors = clinic.doctors.filter(is_active=True)
        
        # Check availability for the given time
        appointment_date = appointment_data.get('appointment_date')
        start_time = appointment_data.get('start_time')
        end_time = appointment_data.get('end_time')
        
        for doctor in doctors:
            # Check if doctor is available at this time
            conflicting = Appointment.objects.filter(
                doctor_profile=doctor,
                appointment_date=appointment_date,
                start_time__lt=end_time,
                end_time__gt=start_time,
                status__in=['scheduled', 'confirmed', 'in_progress']
            )
            if not conflicting.exists():
                return doctor
        
        return None  # No doctor available
    except Exception:
        return None
    
class AppointmentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating appointments"""
    
    class Meta:
        model = Appointment
        fields = [
            'appointment_date', 'start_time', 'end_time',
            'type', 'reason', 'notes', 'status'
        ]
    
    def validate(self, data):
        appointment_date = data.get('appointment_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if appointment_date and start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })
        
        return data


from rest_framework import serializers
from django.db.models import Max
from django.utils import timezone
from .models import QueueEntry


class QueueEntrySerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    urgency_display = serializers.CharField(source='get_urgency_level_display', read_only=True)

    class Meta:
        model = QueueEntry
        fields = [
            'id', 'patient_profile', 'patient_name',
            'doctor_profile', 'doctor_name',
            'queue_position', 'status', 'status_display',
            'reason', 'wait_time_minutes', 'admitted_at',
            'priority', 'urgency_level', 'urgency_display',
            'last_heartbeat', 'is_online',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'queue_position', 'wait_time_minutes',
            'admitted_at', 'last_heartbeat', 'is_online',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'doctor_profile': {'required': False, 'allow_null': True},
            'reason': {'required': True},
            'urgency_level': {'required': False, 'default': 'medium'}
        }

    def get_patient_name(self, obj):
        return obj.patient_profile.profile.user.get_full_name()

    def get_doctor_name(self, obj):
        if obj.doctor_profile:
            return f"Dr. {obj.doctor_profile.profile.user.get_full_name()}"
        return None

    def validate(self, data):
        patient_profile = data.get('patient_profile')
        
        if patient_profile:
            # ✅ Check for ANY existing entry (including old ones)
            existing_entry = QueueEntry.objects.filter(
                patient_profile=patient_profile
            ).first()
            
            if existing_entry:
                # ✅ If entry is active (waiting or in_progress)
                if existing_entry.status in ['waiting', 'in_progress']:
                    raise serializers.ValidationError({
                        'active_entry': {
                            'id': existing_entry.id,
                            'position': existing_entry.queue_position,
                            'status': existing_entry.status,
                            'status_display': existing_entry.get_status_display(),
                            'doctor': self.get_doctor_name(existing_entry),
                            'message': 'You already have an active queue entry. Please wait for your turn.'
                        }
                    })
                else:
                    # ✅ If entry is old (admitted, cancelled), delete it
                    existing_entry.delete()
        
        return data

    def create(self, validated_data):
        # ✅ Force calculation of queue position
        # Count all waiting entries (global position)
        waiting_count = QueueEntry.objects.filter(status='waiting').count()
        
        # ✅ Set queue position to next number
        validated_data['queue_position'] = waiting_count + 1
        
        # Set initial heartbeat
        validated_data['last_heartbeat'] = timezone.now()
        validated_data['is_online'] = True

        # ✅ Log for debugging
        print(f"Creating queue entry with position: {validated_data['queue_position']}")
        print(f"Waiting count: {waiting_count}")

        return super().create(validated_data)