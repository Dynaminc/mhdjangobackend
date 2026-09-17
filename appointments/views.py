# apps/appointments/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from accounts.models import PatientProfile
from .models import Clinic, Appointment, QueueEntry, DoctorAvailability
from .serializers import (
    ClinicSerializer, 
    AppointmentSerializer, 
    AppointmentCreateSerializer,
    AppointmentUpdateSerializer,
    QueueEntrySerializer, 
    DoctorAvailabilitySerializer,
    ClinicWithDoctorsSerializer
)
from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrPatient, IsAdminUser


# ============================================
# Clinic ViewSet
# ============================================
class ClinicViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Clinics.
    Admin can create, update, delete. Everyone can view.
    """
    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    # permission_classes = [IsAdminUser]
    permission_classes = [permissions.AllowAny]
    search_fields = ['name', 'address', 'phone', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_permissions(self):
        permission_classes = [permissions.AllowAny]
        return [permission() for permission in permission_classes]
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve', 'active', 'available_doctors']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @swagger_auto_schema(
        operation_description="Get all clinics",
        responses={200: ClinicSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new clinic",
        request_body=ClinicSerializer,
        responses={201: ClinicSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get a specific clinic",
        responses={200: ClinicSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a clinic",
        request_body=ClinicSerializer,
        responses={200: ClinicSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update a clinic",
        request_body=ClinicSerializer,
        responses={200: ClinicSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a clinic",
        responses={204: 'No Content'}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get all active clinics",
        responses={200: ClinicSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """Get all active clinics"""
        clinics = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(clinics, many=True)
        return Response({
            'status': 'success',
            'count': clinics.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get all appointments for a specific clinic",
        responses={200: AppointmentSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='appointments')
    def appointments(self, request, pk=None):
        """Get all appointments for a specific clinic"""
        clinic = self.get_object()
        appointments = clinic.appointments.all()
        serializer = AppointmentSerializer(appointments, many=True)
        return Response({
            'status': 'success',
            'count': appointments.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get available doctors for a clinic",
        responses={200: openapi.Response('Available doctors', ClinicWithDoctorsSerializer)}
    )
    @action(detail=True, methods=['get'], url_path='available-doctors')
    def available_doctors(self, request, pk=None):
        """Get available doctors for a clinic"""
        clinic = self.get_object()
        serializer = ClinicWithDoctorsSerializer(clinic)
        return Response({
            'status': 'success',
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Search clinics",
        manual_parameters=[
            openapi.Parameter('q', openapi.IN_QUERY, description="Search query", type=openapi.TYPE_STRING),
        ],
        responses={200: ClinicSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """Search clinics by name or address"""
        query = request.query_params.get('q', '')
        if query:
            clinics = self.queryset.filter(
                Q(name__icontains=query) | 
                Q(address__icontains=query) |
                Q(phone__icontains=query)
            )
        else:
            clinics = self.queryset
        
        serializer = self.get_serializer(clinics, many=True)
        return Response({
            'status': 'success',
            'count': clinics.count(),
            'data': serializer.data
        })


# ============================================
# Appointment ViewSet
# ============================================
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Appointments.
    Patients and doctors can manage their appointments.
    """
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['appointment_date', 'status', 'created_at']
    ordering = ['-appointment_date']
    
    def get_serializer_class(self):
        """Return appropriate serializer class based on action"""
        if self.action == 'create':
            return AppointmentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppointmentUpdateSerializer
        return AppointmentSerializer
    
    def get_queryset(self):
        """Filter appointments based on user role"""
        user = self.request.user
        queryset = Appointment.objects.all()
        
        if user.is_staff or user.is_superuser:
            return queryset
        
        if hasattr(user, 'profile'):
            profile = user.profile
            
            # ✅ Check role on Profile
            if profile.role == 'patient':
                # Use PatientProfile if it exists
                if hasattr(profile, 'patient_profile'):
                    return queryset.filter(patient_profile=profile.patient_profile)
            elif profile.role == 'doctor':
                if hasattr(profile, 'doctor_profile'):
                    return queryset.filter(doctor_profile=profile.doctor_profile)
        
        return queryset.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action == 'create':
            # ✅ IsPatient checks profile.role == 'patient'
            permission_classes = [IsPatient]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsDoctorOrPatient]
        elif self.action in ['confirm', 'complete', 'start', 'no_show']:
            permission_classes = [IsDoctor]
        elif self.action == 'cancel':
            permission_classes = [IsDoctorOrPatient]
        elif self.action in ['upcoming', 'history', 'by_date_range', 'my_appointments']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action == 'assign_doctor':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @swagger_auto_schema(
        operation_description="Create a new appointment",
        request_body=AppointmentCreateSerializer,
        responses={201: AppointmentSerializer()}
    )
    def create(self, request, *args, **kwargs):
        """Create a new appointment with auto-creation of PatientProfile if needed"""
        try:
            profile = request.user.profile
            
            # ✅ Check if user is a patient (role-based)
            if profile.role != 'patient':
                return Response({
                    'status': 'error',
                    'message': 'Only patients can create appointments'
                }, status=status.HTTP_403_FORBIDDEN)
            
            # ✅ Auto-create PatientProfile if it doesn't exist
            if not hasattr(profile, 'patient_profile'):
                patient_profile = PatientProfile.objects.create(profile=profile)
                request.data['patient_profile'] = patient_profile.id
            else:
                request.data['patient_profile'] = profile.patient_profile.id
                
        except AttributeError:
            return Response({
                'status': 'error',
                'message': 'User profile not found. Please complete your profile first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)
    
    # ✅ Helper method to ensure patient profile exists
    def _ensure_patient_profile(self, user):
        """Ensure the user has a PatientProfile, create if not"""
        if hasattr(user, 'profile') and user.profile.role == 'patient':
            profile = user.profile
            if not hasattr(profile, 'patient_profile'):
                return PatientProfile.objects.create(profile=profile)
            return profile.patient_profile
        return None
    
    @swagger_auto_schema(
        operation_description="Get all appointments",
        responses={200: AppointmentSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get a specific appointment",
        responses={200: AppointmentSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update an appointment",
        request_body=AppointmentUpdateSerializer,
        responses={200: AppointmentSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update an appointment",
        request_body=AppointmentUpdateSerializer,
        responses={200: AppointmentSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Cancel/Delete an appointment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description='Reason for cancellation')
            }
        ),
        responses={204: 'No Content', 400: 'Bad Request'}
    )
    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()
        reason = request.data.get('reason', '')
        
        # Check permissions
        if not self._is_appointment_participant(request.user, appointment):
            return Response({
                'status': 'error',
                'message': 'You do not have permission to cancel this appointment'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if appointment.is_active:
            appointment.cancel()
            return Response({
                'status': 'success',
                'message': 'Appointment cancelled successfully'
            }, status=status.HTTP_200_OK)
        
        return Response({
            'status': 'error',
            'message': 'This appointment cannot be cancelled'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Confirm an appointment",
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        """Confirm an appointment"""
        appointment = self.get_object()
        
        # Check if user is the doctor
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'doctor':
            return Response({
                'status': 'error',
                'message': 'Only doctors can confirm appointments'
            }, status=status.HTTP_403_FORBIDDEN)
        
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile or doctor_profile != appointment.doctor_profile:
            return Response({
                'status': 'error',
                'message': 'Only the assigned doctor can confirm this appointment'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if appointment.status != 'scheduled':
            return Response({
                'status': 'error',
                'message': f'Appointment is already {appointment.status}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.confirm()
        
        return Response({
            'status': 'success',
            'message': 'Appointment confirmed',
            'data': self.get_serializer(appointment).data
        })
    
    @swagger_auto_schema(
        operation_description="Complete an appointment",
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='complete')
    def complete(self, request, pk=None):
        """Complete an appointment"""
        appointment = self.get_object()
        
        # Check if user is the doctor
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'doctor':
            return Response({
                'status': 'error',
                'message': 'Only doctors can complete appointments'
            }, status=status.HTTP_403_FORBIDDEN)
        
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile or doctor_profile != appointment.doctor_profile:
            return Response({
                'status': 'error',
                'message': 'Only the assigned doctor can complete this appointment'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if appointment.status not in ['confirmed', 'in_progress']:
            return Response({
                'status': 'error',
                'message': 'Appointment must be confirmed or in progress first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.complete()
        
        return Response({
            'status': 'success',
            'message': 'Appointment completed',
            'data': self.get_serializer(appointment).data
        })
    
    @swagger_auto_schema(
        operation_description="Cancel an appointment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'reason': openapi.Schema(type=openapi.TYPE_STRING, description='Reason for cancellation')
            }
        ),
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancel an appointment"""
        appointment = self.get_object()
        reason = request.data.get('reason', '')
        
        # Check permissions
        if not self._is_appointment_participant(request.user, appointment):
            return Response({
                'status': 'error',
                'message': 'You do not have permission to cancel this appointment'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not appointment.is_active:
            return Response({
                'status': 'error',
                'message': 'This appointment cannot be cancelled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.cancel()
        
        return Response({
            'status': 'success',
            'message': 'Appointment cancelled',
            'data': self.get_serializer(appointment).data
        })
    
    @swagger_auto_schema(
        operation_description="Start an appointment (mark as in progress)",
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='start')
    def start(self, request, pk=None):
        """Start an appointment"""
        appointment = self.get_object()
        
        # Check if user is the doctor
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'doctor':
            return Response({
                'status': 'error',
                'message': 'Only doctors can start appointments'
            }, status=status.HTTP_403_FORBIDDEN)
        
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile or doctor_profile != appointment.doctor_profile:
            return Response({
                'status': 'error',
                'message': 'Only the assigned doctor can start this appointment'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if appointment.status not in ['scheduled', 'confirmed']:
            return Response({
                'status': 'error',
                'message': 'Appointment must be scheduled or confirmed first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.start()
        
        return Response({
            'status': 'success',
            'message': 'Appointment started',
            'data': self.get_serializer(appointment).data
        })
    
    @swagger_auto_schema(
        operation_description="Mark appointment as no-show",
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='no-show')
    def no_show(self, request, pk=None):
        """Mark appointment as no-show"""
        appointment = self.get_object()
        
        # Check if user is the doctor
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'doctor':
            return Response({
                'status': 'error',
                'message': 'Only doctors can mark no-show'
            }, status=status.HTTP_403_FORBIDDEN)
        
        doctor_profile = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor_profile or doctor_profile != appointment.doctor_profile:
            return Response({
                'status': 'error',
                'message': 'Only the assigned doctor can mark no-show'
            }, status=status.HTTP_403_FORBIDDEN)
        
        if appointment.status not in ['scheduled', 'confirmed']:
            return Response({
                'status': 'error',
                'message': 'Appointment must be scheduled or confirmed first'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.mark_no_show()
        
        return Response({
            'status': 'success',
            'message': 'Appointment marked as no-show',
            'data': self.get_serializer(appointment).data
        })
    
    @swagger_auto_schema(
        operation_description="Get upcoming appointments",
        responses={200: AppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='upcoming')
    def upcoming(self, request):
        """Get upcoming appointments for current user"""
        queryset = self.get_queryset()
        upcoming = queryset.filter(
            appointment_date__gte=timezone.now().date(),
            status__in=['scheduled', 'confirmed']
        ).order_by('appointment_date', 'start_time')
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response({
            'status': 'success',
            'count': upcoming.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get past appointments history",
        responses={200: AppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='history')
    def history(self, request):
        """Get past appointments history"""
        queryset = self.get_queryset()
        history = queryset.filter(
            appointment_date__lt=timezone.now().date()
        ).order_by('-appointment_date')
        
        serializer = self.get_serializer(history, many=True)
        return Response({
            'status': 'success',
            'count': history.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get appointments by date range",
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Start date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="End date (YYYY-MM-DD)", type=openapi.TYPE_STRING),
        ],
        responses={200: AppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-date-range')
    def by_date_range(self, request):
        """Get appointments within a date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not start_date or not end_date:
            return Response({
                'status': 'error',
                'message': 'start_date and end_date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.get_queryset().filter(
            appointment_date__gte=start_date,
            appointment_date__lte=end_date
        ).order_by('appointment_date', 'start_time')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'count': queryset.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get my appointments (current user)",
        responses={200: AppointmentSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='my-appointments')
    def my_appointments(self, request):
        """Get appointments for the current user (both upcoming and past)"""
        queryset = self.get_queryset().order_by('-appointment_date', '-start_time')
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'count': queryset.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Assign a doctor to an appointment",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'doctor_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Doctor ID to assign'),
            },
            required=['doctor_id']
        ),
        responses={200: AppointmentSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='assign-doctor')
    def assign_doctor(self, request, pk=None):
        """Assign a doctor to an appointment"""
        appointment = self.get_object()
        doctor_id = request.data.get('doctor_id')
        
        if not doctor_id:
            return Response({
                'status': 'error',
                'message': 'doctor_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from accounts.models import DoctorProfile
        doctor = get_object_or_404(DoctorProfile, id=doctor_id)
        
        # Check if doctor belongs to the clinic
        if doctor not in appointment.clinic.doctors.all():
            return Response({
                'status': 'error',
                'message': 'Doctor does not work at this clinic'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        appointment.assign_doctor(doctor)
        
        return Response({
            'status': 'success',
            'message': 'Doctor assigned successfully',
            'data': self.get_serializer(appointment).data
        })
    
    # ============================================
    # HELPER METHODS
    # ============================================
    
    def _is_appointment_participant(self, user, appointment):
        """
        Check if a user is a participant in the appointment
        (either the patient or the doctor)
        """
        if not user or not hasattr(user, 'profile'):
            return False
        
        profile = user.profile
        
        # Check if user is the patient
        if profile.role == 'patient':
            patient_profile = getattr(profile, 'patient_profile', None)
            if patient_profile and appointment.patient_profile == patient_profile:
                return True
        
        # Check if user is the doctor
        if profile.role == 'doctor':
            doctor_profile = getattr(profile, 'doctor_profile', None)
            if doctor_profile and appointment.doctor_profile == doctor_profile:
                return True
        
        # Admin can access anything
        if user.is_staff or user.is_superuser:
            return True
        
        return False
    
# ============================================
# QueueEntry ViewSet
# ============================================
# apps/appointments/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import QueueEntry
from .serializers import QueueEntrySerializer
from accounts.permissions import IsPatient, IsDoctor, IsAdminUser


class QueueEntryViewSet(viewsets.ModelViewSet):
    queryset = QueueEntry.objects.all()
    serializer_class = QueueEntrySerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['queue_position', 'wait_time_minutes', 'created_at']
    ordering = ['queue_position']

    def get_queryset(self):
        user = self.request.user
        queryset = QueueEntry.objects.all()

        if user.is_staff or user.is_superuser:
            return queryset

        try:
            profile = user.profile
            if hasattr(profile, 'patient_profile'):
                return queryset.filter(patient_profile=profile.patient_profile)
            elif hasattr(profile, 'doctor_profile'):
                return queryset.filter(doctor_profile=profile.doctor_profile)
        except:
            return queryset.none()
        return queryset.none()

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsPatient]
        elif self.action in ['admit', 'start_progress', 'complete']:
            self.permission_classes = [IsDoctor]
        elif self.action in ['update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in self.permission_classes]

    @swagger_auto_schema(
        operation_description="Create a new queue entry (doctor_profile is optional)",
        request_body=QueueEntrySerializer,
        responses={201: QueueEntrySerializer()}
    )
    def create(self, request, *args, **kwargs):
        try:
            profile = request.user.profile
            if profile.role != 'patient':
                return Response({
                    'status': 'error',
                    'message': 'Only patients can join the queue'
                }, status=status.HTTP_403_FORBIDDEN)

            patient_profile = getattr(profile, 'patient_profile', None)
            if not patient_profile:
                return Response({
                    'status': 'error',
                    'message': 'Patient profile not found. Please complete your profile first.'
                }, status=status.HTTP_400_BAD_REQUEST)

            # ✅ Check for existing entry BEFORE trying to create
            existing_entry = QueueEntry.objects.filter(
                patient_profile=patient_profile
            ).first()
            
            if existing_entry:
                # ✅ If active, return helpful message
                if existing_entry.status in ['waiting', 'in_progress']:
                    return Response({
                        'status': 'error',
                        'message': 'You already have an active queue entry.',
                        'active_entry': {
                            'id': existing_entry.id,
                            'position': existing_entry.queue_position,
                            'status': existing_entry.status,
                            'status_display': existing_entry.get_status_display(),
                            'doctor_name': f"Dr. {existing_entry.doctor_profile.profile.user.get_full_name()}" if existing_entry.doctor_profile else 'Not assigned',
                            'wait_time': existing_entry.wait_time_minutes,
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # ✅ If old entry, delete it
                    existing_entry.delete()

            # Set patient_profile in request data
            request.data['patient_profile'] = patient_profile.id

        except AttributeError:
            return Response({
                'status': 'error',
                'message': 'User profile not found.'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # ✅ Use the serializer to create the entry
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            # ✅ Log the created entry
            print(f"✅ Queue entry created: {serializer.instance}")
            print(f"✅ Queue position: {serializer.instance.queue_position}")
            
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
            
        except IntegrityError as e:
            if 'UNIQUE constraint' in str(e) or 'patient_profile' in str(e):
                return Response({
                    'status': 'error',
                    'message': 'You already have a queue entry. Please wait for your turn or cancel your existing entry.'
                }, status=status.HTTP_400_BAD_REQUEST)
            raise e
        except Exception as e:
            print(f"❌ Error creating queue entry: {e}")
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

# apps/appointments/views.py
# apps/appointments/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .queue_service import queue
from accounts.permissions import IsPatient, IsDoctor


# apps/appointments/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .queue_service import queue
from accounts.permissions import IsPatient, IsDoctor


class QueueViewSet(viewsets.GenericViewSet):
    """
    Simple queue management using a list/array
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get current queue",
        responses={200: openapi.Response('Queue list')}
    )
    @action(detail=False, methods=['get'], url_path='list')
    def get_queue(self, request):
        """Get all patients in queue"""
        queue_data = queue.get_queue()
        return Response({
            'status': 'success',
            'count': len(queue_data),
            'online_count': sum(1 for p in queue_data if p['is_online']),
            'data': queue_data
        })
    
    @swagger_auto_schema(
        operation_description="Get my queue position - also acts as heartbeat",
        responses={200: openapi.Response('Queue position')}
    )
    @action(detail=False, methods=['get'], url_path='my-position')
    def my_position(self, request):
        """Get current patient's queue position. Every call also acts as heartbeat!"""
        if not hasattr(request.user.profile, 'patient_profile'):
            return Response({
                'status': 'error',
                'message': 'Only patients can check their position'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient = request.user.profile
        print(queue.get_queue())
        result = queue.get_position(patient.id)
        
        if result:
            return Response({
                'status': 'success',
                'in_queue': True,
                'position': result['position'],
                'patients_ahead': result['patients_ahead'],
                'queue_length': result['queue_length'],
                'is_online': True
            })
        
        return Response({
            'status': 'success',
            'in_queue': False,
            'message': 'You are not in the queue'
        })
    
    @swagger_auto_schema(
        operation_description="Join the queue as current user",
        responses={200: openapi.Response('Queue position')}
    )
    @action(detail=False, methods=['post'], url_path='join-me')
    def join_me(self, request):
        """Current patient joins the queue"""
        if not hasattr(request.user.profile, 'patient_profile'):
            return Response({
                'status': 'error',
                'message': 'Only patients can join the queue'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient = request.user.profile
        patient_id = patient.id
        name = request.user.get_full_name()
        
        if queue.is_in_queue(patient_id):
            position = queue.get_position(patient_id)
            return Response({
                'status': 'error',
                'message': 'You are already in the queue',
                'position': position['position'] if position else None
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = queue.join(patient_id, name)
        
        if 'error' in result:
            return Response({
                'status': 'error',
                'message': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': f'You joined the queue',
            'position': result['position'],
            'patients_ahead': result['patients_ahead'],
            'queue_length': result['queue_length']
        })
    
    @swagger_auto_schema(
        operation_description="Leave the queue as current user",
        responses={200: openapi.Response('Left queue')}
    )
    @action(detail=False, methods=['post'], url_path='leave-me')
    def leave_me(self, request):
        """Current patient leaves the queue"""
        if not hasattr(request.user.profile, 'patient_profile'):
            return Response({
                'status': 'error',
                'message': 'Only patients can leave the queue'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient = request.user.profile.patient_profile
        result = queue.leave(patient.id)
        
        if 'error' in result:
            return Response({
                'status': 'error',
                'message': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': 'You left the queue'
        })
    
    @swagger_auto_schema(
        operation_description="Get next patient (doctor only)",
        responses={200: openapi.Response('Next patient')}
    )
    @action(detail=False, methods=['post'], url_path='next')
    def next_patient(self, request):
        """Doctor gets the next patient (pop from front)"""
        if not hasattr(request.user.profile, 'doctor_profile'):
            return Response({
                'status': 'error',
                'message': 'Only doctors can get the next patient'
            }, status=status.HTTP_403_FORBIDDEN)
        
        result = queue.next()
        
        if 'error' in result:
            return Response({
                'status': 'error',
                'message': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get patient details
        from accounts.models import PatientProfile
        try:
            patient = PatientProfile.objects.get(id=result['patient_id'])
            return Response({
                'status': 'success',
                'message': f'Patient {patient.profile.user.get_full_name()} admitted',
                'patient': {
                    'id': patient.id,
                    'name': patient.profile.user.get_full_name(),
                    'email': patient.profile.user.email
                },
                'remaining': result['remaining']
            })
        except PatientProfile.DoesNotExist:
            return Response({
                'status': 'success',
                'patient_id': result['patient_id'],
                'remaining': result['remaining']
            })
    
    @swagger_auto_schema(
        operation_description="✅ Admit a specific patient (doctor only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'patient_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Patient profile ID to admit'
                ),
            },
            required=['patient_id']
        ),
        responses={200: openapi.Response('Patient admitted')}
    )
    @action(detail=False, methods=['post'], url_path='admit')
    def admit_patient(self, request):
        """
        ✅ Admit a specific patient from the queue
        This pops them from the queue and marks them as admitted
        """
        print(request.user.profile) #hasattr(request.user.profile, 'doctor_profile')
        if not request.user.profile.role == 'doctor':
            return Response({
                'status': 'error',
                'message': 'Only doctors can admit patients'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({
                'status': 'error',
                'message': 'patient_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = queue.admit(patient_id)
        
        if 'error' in result:
            return Response({
                'status': 'error',
                'message': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get patient details
        from accounts.models import PatientProfile
        try:
            patient = PatientProfile.objects.get(id=patient_id)
            return Response({
                'status': 'success',
                'message': result['message'],
                'patient': {
                    'id': patient.id,
                    'name': patient.profile.user.get_full_name(),
                    'email': patient.profile.user.email
                },
                'remaining': result['remaining']
            })
        except PatientProfile.DoesNotExist:
            return Response({
                'status': 'success',
                'message': result['message'],
                'patient_id': patient_id,
                'remaining': result['remaining']
            })
    
    @swagger_auto_schema(
        operation_description="✅ Complete a consultation (doctor only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'patient_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Patient profile ID to complete'
                ),
            },
            required=['patient_id']
        ),
        responses={200: openapi.Response('Patient completed')}
    )
    @action(detail=False, methods=['post'], url_path='complete')
    def complete_patient(self, request):
        """
        ✅ Mark a patient's consultation as complete
        """
        if not hasattr(request.user.profile, 'doctor_profile'):
            return Response({
                'status': 'error',
                'message': 'Only doctors can complete consultations'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({
                'status': 'error',
                'message': 'patient_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = queue.complete(patient_id)
        
        if 'error' in result:
            return Response({
                'status': 'error',
                'message': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'status': 'success',
            'message': result['message'],
            'patient_id': patient_id
        })
    
    @swagger_auto_schema(
        operation_description="✅ Admit and complete in one go (doctor only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'patient_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Patient profile ID'
                ),
            },
            required=['patient_id']
        ),
        responses={200: openapi.Response('Patient admitted and completed')}
    )
    @action(detail=False, methods=['post'], url_path='admit-and-complete')
    def admit_and_complete(self, request):
        """
        ✅ Admit and immediately complete a patient (for quick consultations)
        """
        if not hasattr(request.user.profile, 'doctor_profile'):
            return Response({
                'status': 'error',
                'message': 'Only doctors can perform this action'
            }, status=status.HTTP_403_FORBIDDEN)
        
        patient_id = request.data.get('patient_id')
        if not patient_id:
            return Response({
                'status': 'error',
                'message': 'patient_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = queue.admit_and_complete(patient_id)
        
        if 'error' in result:
            return Response({
                'status': 'error',
                'message': result['error']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        from accounts.models import PatientProfile
        try:
            patient = PatientProfile.objects.get(id=patient_id)
            return Response({
                'status': 'success',
                'message': f'Patient {patient.profile.user.get_full_name()} admitted and completed',
                'patient': {
                    'id': patient.id,
                    'name': patient.profile.user.get_full_name()
                }
            })
        except PatientProfile.DoesNotExist:
            return Response({
                'status': 'success',
                'message': 'Patient admitted and completed',
                'patient_id': patient_id
            })
    
    @swagger_auto_schema(
        operation_description="Get admitted patients history (doctor only)",
        responses={200: openapi.Response('Admitted patients')}
    )
    @action(detail=False, methods=['get'], url_path='admitted')
    def get_admitted(self, request):
        """Get list of admitted patients (doctor only)"""
        if not hasattr(request.user.profile, 'doctor_profile'):
            return Response({
                'status': 'error',
                'message': 'Only doctors can view admitted patients'
            }, status=status.HTTP_403_FORBIDDEN)
        
        admitted = queue.get_admitted()
        return Response({
            'status': 'success',
            'count': len(admitted),
            'data': admitted
        })
    
    @swagger_auto_schema(
        operation_description="Get completed patients history (doctor only)",
        responses={200: openapi.Response('Completed patients')}
    )
    @action(detail=False, methods=['get'], url_path='completed')
    def get_completed(self, request):
        """Get list of completed patients (doctor only)"""
        if not hasattr(request.user.profile, 'doctor_profile'):
            return Response({
                'status': 'error',
                'message': 'Only doctors can view completed patients'
            }, status=status.HTTP_403_FORBIDDEN)
        
        completed = queue.get_completed()
        return Response({
            'status': 'success',
            'count': len(completed),
            'data': completed
        })
    
    @swagger_auto_schema(
        operation_description="Get queue length",
        responses={200: openapi.Response('Queue length')}
    )
    @action(detail=False, methods=['get'], url_path='length')
    def queue_length(self, request):
        """Get number of patients in queue"""
        return Response({
            'status': 'success',
            'length': len(queue)
        })
    
    @swagger_auto_schema(
        operation_description="Get online status of queue (doctor only)",
        responses={200: openapi.Response('Online status')}
    )
    @action(detail=False, methods=['get'], url_path='online-status')
    def online_status(self, request):
        """Get online/offline status of all queue patients (doctor only)"""
        if not hasattr(request.user.profile, 'doctor_profile'):
            return Response({
                'status': 'error',
                'message': 'Only doctors can view online status'
            }, status=status.HTTP_403_FORBIDDEN)
        
        queue_data = queue.get_queue()
        online = [p for p in queue_data if p['is_online']]
        offline = [p for p in queue_data if not p['is_online']]
        
        return Response({
            'status': 'success',
            'total': len(queue_data),
            'online_count': len(online),
            'offline_count': len(offline),
            'online_patients': online,
            'offline_patients': offline
        })
    
    @swagger_auto_schema(
        operation_description="Cleanup inactive patients (admin only)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'timeout': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Timeout in seconds (default: 120)',
                    default=120
                )
            }
        ),
        responses={200: openapi.Response('Cleanup result')}
    )
    @action(detail=False, methods=['post'], url_path='cleanup')
    def cleanup_queue(self, request):
        """Remove inactive patients from queue (admin only)"""
        if not request.user.is_staff:
            return Response({
                'status': 'error',
                'message': 'Only admins can clean up the queue'
            }, status=status.HTTP_403_FORBIDDEN)
        
        timeout = request.data.get('timeout', 120)
        result = queue.cleanup_inactive(timeout)
        
        return Response({
            'status': 'success',
            'message': f'Removed {result["removed"]} inactive patients',
            'remaining': result['remaining']
        })
# DoctorAvailability ViewSet
# ============================================
class DoctorAvailabilityViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Doctor Availability.
    """
    queryset = DoctorAvailability.objects.all()
    serializer_class = DoctorAvailabilitySerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['day_of_week', 'start_time', 'created_at']
    ordering = ['day_of_week', 'start_time']
    
    def get_queryset(self):
        """Filter availability based on user role"""
        user = self.request.user
        queryset = DoctorAvailability.objects.all()
        
        if user.is_staff or user.is_superuser:
            return queryset
        
        try:
            profile = user.profile
            if hasattr(profile, 'doctor_profile'):
                return queryset.filter(doctor_profile=profile.doctor_profile)
        except:
            return queryset.none()
        
        return queryset.none()
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]
        elif self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsDoctor]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @swagger_auto_schema(
        operation_description="Get all doctor availability slots",
        responses={200: DoctorAvailabilitySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new availability slot",
        request_body=DoctorAvailabilitySerializer,
        responses={201: DoctorAvailabilitySerializer()}
    )
    def create(self, request, *args, **kwargs):
        # Add doctor_profile from request user
        try:
            request.data['doctor_profile'] = request.user.profile.doctor_profile.id
        except AttributeError:
            return Response({
                'status': 'error',
                'message': 'Doctor profile not found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get a specific availability slot",
        responses={200: DoctorAvailabilitySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update an availability slot",
        request_body=DoctorAvailabilitySerializer,
        responses={200: DoctorAvailabilitySerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update an availability slot",
        request_body=DoctorAvailabilitySerializer,
        responses={200: DoctorAvailabilitySerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete an availability slot",
        responses={204: 'No Content'}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get availability for a specific doctor",
        manual_parameters=[
            openapi.Parameter('doctor_id', openapi.IN_QUERY, description="Doctor ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('day', openapi.IN_QUERY, description="Day of week (0-6)", type=openapi.TYPE_INTEGER),
        ],
        responses={200: DoctorAvailabilitySerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-doctor')
    def by_doctor(self, request):
        """Get availability for a specific doctor"""
        doctor_id = request.query_params.get('doctor_id')
        day = request.query_params.get('day')
        
        if not doctor_id:
            return Response({
                'status': 'error',
                'message': 'doctor_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        queryset = self.queryset.filter(doctor_profile_id=doctor_id, is_available=True)
        
        if day is not None:
            queryset = queryset.filter(day_of_week=day)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'count': queryset.count(),
            'data': serializer.data
        })
    
    @swagger_auto_schema(
        operation_description="Get availability for a specific date",
        manual_parameters=[
            openapi.Parameter('doctor_id', openapi.IN_QUERY, description="Doctor ID", type=openapi.TYPE_INTEGER, required=True),
            openapi.Parameter('date', openapi.IN_QUERY, description="Date (YYYY-MM-DD)", type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: DoctorAvailabilitySerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-date')
    def by_date(self, request):
        """Get availability for a specific date"""
        from datetime import datetime
        
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')
        
        if not doctor_id or not date_str:
            return Response({
                'status': 'error',
                'message': 'doctor_id and date are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            day_of_week = date.weekday()
        except ValueError:
            return Response({
                'status': 'error',
                'message': 'Invalid date format. Use YYYY-MM-DD'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get regular availability for this day
        queryset = self.queryset.filter(
            doctor_profile_id=doctor_id,
            day_of_week=day_of_week,
            is_available=True
        )
        
        # Check for specific date overrides
        specific_overrides = self.queryset.filter(
            doctor_profile_id=doctor_id,
            specific_date=date
        )
        
        # If there are specific overrides, use those instead
        if specific_overrides.exists():
            queryset = specific_overrides.filter(is_available=True)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'date': date_str,
            'day': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week],
            'count': queryset.count(),
            'data': serializer.data
        })