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
        if not obj.doctor_profile_id:
            return None
        user = obj.doctor_profile.profile.user
        return f"Dr. {user.get_full_name() or user.email}"

ACTIVE_STATUSES = ('scheduled', 'confirmed', 'in_progress')

# apps/appointments/serializers.py
from rest_framework import serializers
from django.utils import timezone

from .models import Appointment


ACTIVE_STATUSES = ('scheduled', 'confirmed', 'in_progress')
INSTANT_MARKERS = ('instant', 'instant consultation', 'walk-in', 'walk in')
# apps/appointments/serializers.py

class AppointmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = [
            'id',     
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
            'patient_profile': {'required': True},
        }

    def validate(self, data):
        from django.db.models import Q

        clinic = data.get('clinic')
        doctor_profile = data.get('doctor_profile')
        appointment_date = data.get('appointment_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        patient_profile = data.get('patient_profile')
        appointment_type = data.get('type', 'physical')
        new_notes = data.get('notes') or ''
        new_reason = (data.get('reason') or '').lower()

        def _is_instant_note(note: str) -> bool:
            return bool(note) and 'instant consultation' in note.lower()

        new_is_instant_virtual = (
            appointment_type == 'virtual'
            and (_is_instant_note(new_notes) or 'instant' in new_reason)
        )

        # ─────────────────────────────────────────────
        # 1. Time sanity — skipped for instant (can span midnight)
        # ─────────────────────────────────────────────
        if (
            not new_is_instant_virtual
            and appointment_date
            and start_time
            and end_time
        ):
            if start_time >= end_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time'
                })

        # ─────────────────────────────────────────────
        # 2. Doctor belongs to clinic
        # ─────────────────────────────────────────────
        if clinic and clinic.requires_doctor_selection:
            if not doctor_profile:
                raise serializers.ValidationError({
                    'doctor_profile': 'This clinic requires you to select a doctor'
                })
            if doctor_profile not in clinic.doctors.all():
                raise serializers.ValidationError({
                    'doctor_profile': 'Selected doctor does not work at this clinic'
                })
        else:
            if (
                doctor_profile
                and clinic
                and doctor_profile not in clinic.doctors.all()
            ):
                raise serializers.ValidationError({
                    'doctor_profile': 'Selected doctor does not work at this clinic'
                })

        # ─────────────────────────────────────────────
        # 3. Doctor overlap — skipped for instant
        # ─────────────────────────────────────────────
        if (
            not new_is_instant_virtual
            and doctor_profile
            and appointment_date
            and start_time
            and end_time
        ):
            conflicting = Appointment.objects.filter(
                doctor_profile=doctor_profile,
                appointment_date=appointment_date,
                start_time__lt=end_time,
                end_time__gt=start_time,
                status__in=ACTIVE_STATUSES,
            )
            if self.instance:
                conflicting = conflicting.exclude(id=self.instance.id)

            conflicting = conflicting.exclude(
                Q(consultation__status='completed')
                | Q(consultation__status='cancelled')
            )

            if conflicting.exists():
                raise serializers.ValidationError({
                    'appointment_date': 'Doctor already has an appointment at this time'
                })

        # ─────────────────────────────────────────────
        # 4. Duplicate open appointment of the same category
        # ─────────────────────────────────────────────
        if patient_profile and appointment_date:

            # ── Step A: If creating a NEW INSTANT VIRTUAL,
            #    auto-close every other scheduled instant-virtual
            #    for this patient on this date. Doesn't rely on
            #    consultation status — instant means "one at a time".
            if new_is_instant_virtual:
                others = Appointment.objects.filter(
                    patient_profile=patient_profile,
                    appointment_date=appointment_date,
                    type='virtual',
                    status__in=['scheduled', 'confirmed', 'in_progress'],
                )
                if self.instance:
                    others = others.exclude(id=self.instance.id)

                instant_ids = [
                    a.id for a in others
                    if _is_instant_note(a.notes or '')
                ]
                if instant_ids:
                    Appointment.objects.filter(id__in=instant_ids).update(
                        status='completed'
                    )

            # ── Step A2: Also close any stale appointment whose
            #    consultation is finished (for non-instant categories)
            stale = Appointment.objects.filter(
                patient_profile=patient_profile,
                status__in=ACTIVE_STATUSES,
            ).filter(
                Q(consultation__status='completed')
                | Q(consultation__status='cancelled')
            )
            if self.instance:
                stale = stale.exclude(id=self.instance.id)
            stale.update(status='completed')

            # ── Step B: Re-query — closed rows are now filtered out
            duplicate_qs = Appointment.objects.filter(
                patient_profile=patient_profile,
                appointment_date=appointment_date,
                status__in=ACTIVE_STATUSES,
            )
            if self.instance:
                duplicate_qs = duplicate_qs.exclude(id=self.instance.id)

            new_is_scheduled_virtual = (
                appointment_type == 'virtual' and not new_is_instant_virtual
            )
            new_is_physical = appointment_type == 'physical'

            # ── Step C: Look for a same-category live conflict
            conflict = None
            for existing in duplicate_qs:
                ex_notes = existing.notes or ''
                ex_is_instant_virtual = (
                    existing.type == 'virtual' and _is_instant_note(ex_notes)
                )
                ex_is_scheduled_virtual = (
                    existing.type == 'virtual' and not ex_is_instant_virtual
                )
                ex_is_physical = existing.type == 'physical'

                same_category = (
                    (new_is_physical and ex_is_physical)
                    or (new_is_instant_virtual and ex_is_instant_virtual)
                    or (new_is_scheduled_virtual and ex_is_scheduled_virtual)
                )
                if same_category:
                    conflict = existing
                    break

            if conflict:
                if new_is_physical:
                    category_label = 'physical'
                elif new_is_instant_virtual:
                    category_label = 'instant virtual'
                else:
                    category_label = 'scheduled virtual'

                raise serializers.ValidationError({
                    'detail': (
                        f"This patient already has an open {category_label} "
                        f"appointment on {appointment_date} "
                        f"(#{conflict.id}, status: {conflict.status}). "
                        f"Close, complete, or cancel it before creating another."
                    ),
                    'existing_appointment_id': conflict.id,
                    'existing_status': conflict.status,
                    'existing_category': category_label,
                })

        return data

    def create(self, validated_data):
        from django.utils import timezone
        from .utils import auto_assign_doctor
        from consultations.models import Consultation

        patient_profile = validated_data.get('patient_profile')
        clinic = validated_data.get('clinic')
        doctor_profile = validated_data.get('doctor_profile', None)

        # Auto-assign only when a clinic exists
        if not doctor_profile and clinic and not clinic.requires_doctor_selection:
            doctor_profile = auto_assign_doctor(clinic, validated_data)

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
            status='scheduled',
        )

        if doctor_profile and not validated_data.get('doctor_profile'):
            appointment.doctor_assigned_at = timezone.now()
            appointment.save(update_fields=['doctor_assigned_at'])

        # ✅ Always create a consultation — doctor may be null for instant
        if not hasattr(appointment, 'consultation'):
            Consultation.objects.create(
                appointment=appointment,
                patient_profile=patient_profile,
                doctor_profile=doctor_profile,   # may be None
                type=appointment.type,
                clinic_location=clinic.name if clinic else '',
                status='ongoing',
            )

        return appointment
    # def create(self, validated_data):
    #     from django.utils import timezone
    #     from .utils import auto_assign_doctor
    #     from consultations.models import Consultation

    #     patient_profile = validated_data.get('patient_profile')
    #     clinic = validated_data.get('clinic')
    #     doctor_profile = validated_data.get('doctor_profile', None)

    #     if not doctor_profile and clinic and not clinic.requires_doctor_selection:
    #         doctor_profile = auto_assign_doctor(clinic, validated_data)

    #     appointment = Appointment.objects.create(
    #         patient_profile=patient_profile,
    #         clinic=clinic,
    #         doctor_profile=doctor_profile,
    #         appointment_date=validated_data.get('appointment_date'),
    #         start_time=validated_data.get('start_time'),
    #         end_time=validated_data.get('end_time'),
    #         type=validated_data.get('type', 'physical'),
    #         reason=validated_data.get('reason', ''),
    #         notes=validated_data.get('notes', ''),
    #         status='scheduled',
    #     )

    #     if doctor_profile and not validated_data.get('doctor_profile'):
    #         appointment.doctor_assigned_at = timezone.now()
    #         appointment.save(update_fields=['doctor_assigned_at'])

    #     # ✅ Auto-create the consultation when a doctor is assigned
    #     if doctor_profile and not hasattr(appointment, 'consultation'):
    #         Consultation.objects.create(
    #             appointment=appointment,
    #             patient_profile=patient_profile,
    #             doctor_profile=doctor_profile,
    #             type=appointment.type,
    #             clinic_location=clinic.name if clinic else '',
    #             status='ongoing',
    #         )

    #     return appointment
    
    
# class AppointmentCreateSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Appointment
#         fields = [
#             'patient_profile',
#             'clinic',
#             'appointment_date',
#             'start_time',
#             'end_time',
#             'type',
#             'reason',
#             'notes',
#             'doctor_profile',
#         ]
#         extra_kwargs = {
#             'doctor_profile': {'required': False, 'allow_null': True},
#             'patient_profile': {'required': True},
#         }


#     def _is_instant(self, data):
#         """Instant consultations are identified by their reason (case-insensitive)."""
#         reason = (data.get('reason') or '').strip().lower()
#         return any(marker in reason for marker in INSTANT_MARKERS)

#     def validate(self, data):
#         from django.db.models import Q

#         clinic = data.get('clinic')
#         doctor_profile = data.get('doctor_profile')
#         appointment_date = data.get('appointment_date')
#         start_time = data.get('start_time')
#         end_time = data.get('end_time')
#         patient_profile = data.get('patient_profile')
#         appointment_type = data.get('type', 'physical')
#         new_notes = data.get('notes') or ''
#         new_reason = (data.get('reason') or '').lower()

#         def _is_instant_note(note: str) -> bool:
#             return bool(note) and 'instant consultation' in note.lower()

#         new_is_instant_virtual = (
#             appointment_type == 'virtual'
#             and (_is_instant_note(new_notes) or 'instant' in new_reason)
#         )

#         # ─────────────────────────────────────────────
#         # 1. Time sanity — skipped for instant (can span midnight)
#         # ─────────────────────────────────────────────
#         if (
#             not new_is_instant_virtual
#             and appointment_date
#             and start_time
#             and end_time
#         ):
#             if start_time >= end_time:
#                 raise serializers.ValidationError({
#                     'end_time': 'End time must be after start time'
#                 })

#         # ─────────────────────────────────────────────
#         # 2. Doctor belongs to clinic
#         # ─────────────────────────────────────────────
#         if clinic and clinic.requires_doctor_selection:
#             if not doctor_profile:
#                 raise serializers.ValidationError({
#                     'doctor_profile': 'This clinic requires you to select a doctor'
#                 })
#             if doctor_profile not in clinic.doctors.all():
#                 raise serializers.ValidationError({
#                     'doctor_profile': 'Selected doctor does not work at this clinic'
#                 })
#         else:
#             if (
#                 doctor_profile
#                 and clinic
#                 and doctor_profile not in clinic.doctors.all()
#             ):
#                 raise serializers.ValidationError({
#                     'doctor_profile': 'Selected doctor does not work at this clinic'
#                 })

#         # ─────────────────────────────────────────────
#         # 3. Doctor overlap — skipped for instant
#         # ─────────────────────────────────────────────
#         if (
#             not new_is_instant_virtual
#             and doctor_profile
#             and appointment_date
#             and start_time
#             and end_time
#         ):
#             conflicting = Appointment.objects.filter(
#                 doctor_profile=doctor_profile,
#                 appointment_date=appointment_date,
#                 start_time__lt=end_time,
#                 end_time__gt=start_time,
#                 status__in=ACTIVE_STATUSES,
#             )
#             if self.instance:
#                 conflicting = conflicting.exclude(id=self.instance.id)

#             conflicting = conflicting.exclude(
#                 Q(consultation__status='completed')
#                 | Q(consultation__status='cancelled')
#             )

#             if conflicting.exists():
#                 raise serializers.ValidationError({
#                     'appointment_date': 'Doctor already has an appointment at this time'
#                 })

#         # ─────────────────────────────────────────────
#         # 4. Duplicate open appointment of the same category
#         # ─────────────────────────────────────────────
#         if patient_profile and appointment_date:

#             # ── Step A: If creating a NEW INSTANT VIRTUAL,
#             #    auto-close every other scheduled instant-virtual
#             #    for this patient on this date. Doesn't rely on
#             #    consultation status — instant means "one at a time".
#             if new_is_instant_virtual:
#                 others = Appointment.objects.filter(
#                     patient_profile=patient_profile,
#                     appointment_date=appointment_date,
#                     type='virtual',
#                     status__in=['scheduled', 'confirmed', 'in_progress'],
#                 )
#                 if self.instance:
#                     others = others.exclude(id=self.instance.id)

#                 instant_ids = [
#                     a.id for a in others
#                     if _is_instant_note(a.notes or '')
#                 ]
#                 if instant_ids:
#                     Appointment.objects.filter(id__in=instant_ids).update(
#                         status='completed'
#                     )

#             # ── Step A2: Also close any stale appointment whose
#             #    consultation is finished (for non-instant categories)
#             stale = Appointment.objects.filter(
#                 patient_profile=patient_profile,
#                 status__in=ACTIVE_STATUSES,
#             ).filter(
#                 Q(consultation__status='completed')
#                 | Q(consultation__status='cancelled')
#             )
#             if self.instance:
#                 stale = stale.exclude(id=self.instance.id)
#             stale.update(status='completed')

#             # ── Step B: Re-query — closed rows are now filtered out
#             duplicate_qs = Appointment.objects.filter(
#                 patient_profile=patient_profile,
#                 appointment_date=appointment_date,
#                 status__in=ACTIVE_STATUSES,
#             )
#             if self.instance:
#                 duplicate_qs = duplicate_qs.exclude(id=self.instance.id)

#             new_is_scheduled_virtual = (
#                 appointment_type == 'virtual' and not new_is_instant_virtual
#             )
#             new_is_physical = appointment_type == 'physical'

#             # ── Step C: Look for a same-category live conflict
#             conflict = None
#             for existing in duplicate_qs:
#                 ex_notes = existing.notes or ''
#                 ex_is_instant_virtual = (
#                     existing.type == 'virtual' and _is_instant_note(ex_notes)
#                 )
#                 ex_is_scheduled_virtual = (
#                     existing.type == 'virtual' and not ex_is_instant_virtual
#                 )
#                 ex_is_physical = existing.type == 'physical'

#                 same_category = (
#                     (new_is_physical and ex_is_physical)
#                     or (new_is_instant_virtual and ex_is_instant_virtual)
#                     or (new_is_scheduled_virtual and ex_is_scheduled_virtual)
#                 )
#                 if same_category:
#                     conflict = existing
#                     break

#             if conflict:
#                 if new_is_physical:
#                     category_label = 'physical'
#                 elif new_is_instant_virtual:
#                     category_label = 'instant virtual'
#                 else:
#                     category_label = 'scheduled virtual'

#                 raise serializers.ValidationError({
#                     'detail': (
#                         f"This patient already has an open {category_label} "
#                         f"appointment on {appointment_date} "
#                         f"(#{conflict.id}, status: {conflict.status}). "
#                         f"Close, complete, or cancel it before creating another."
#                     ),
#                     'existing_appointment_id': conflict.id,
#                     'existing_status': conflict.status,
#                     'existing_category': category_label,
#                 })

#         return data

#     def create(self, validated_data):
#         from .utils import auto_assign_doctor

#         patient_profile = validated_data.get('patient_profile')
#         clinic = validated_data.get('clinic')
#         doctor_profile = validated_data.get('doctor_profile', None)

#         if not doctor_profile and clinic and not clinic.requires_doctor_selection:
#             doctor_profile = auto_assign_doctor(clinic, validated_data)

#         appointment = Appointment.objects.create(
#             patient_profile=patient_profile,
#             clinic=clinic,
#             doctor_profile=doctor_profile,
#             appointment_date=validated_data.get('appointment_date'),
#             start_time=validated_data.get('start_time'),
#             end_time=validated_data.get('end_time'),
#             type=validated_data.get('type', 'physical'),
#             reason=validated_data.get('reason', ''),
#             notes=validated_data.get('notes', ''),
#             status='scheduled',
#         )

#         if doctor_profile and not validated_data.get('doctor_profile'):
#             appointment.doctor_assigned_at = timezone.now()
#             appointment.save()

#         return appointment
    

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