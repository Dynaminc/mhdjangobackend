# apps/prescriptions/viewsets.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    MedicationCatalog,
    Prescription,
    RefillRequest,
    MedicationInteraction,
    MedicationSchedule,
    MedicationAdherence
)
from .serializers import (
    MedicationCatalogSerializer,
    MedicationCatalogListSerializer,
    PrescriptionSerializer,
    PrescriptionListSerializer,
    PrescriptionCreateSerializer,
    PrescriptionWithSchedulesSerializer,
    PrescriptionRefillSerializer,
    PrescriptionStatusUpdateSerializer,
    RefillRequestSerializer,
    RefillRequestCreateSerializer,
    RefillRequestApproveSerializer,
    MedicationInteractionSerializer,
    MedicationScheduleSerializer,
    MedicationAdherenceSerializer,
    MedicationAdherenceStatsSerializer,
    MedicationSearchSerializer
)
from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrPatient
from accounts.models import PatientProfile


class MedicationCatalogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medication catalog
    
    Provides CRUD operations for the master list of available medications
    """
    
    queryset = MedicationCatalog.objects.filter(is_active=True)
    permission_classes = [IsDoctor]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MedicationCatalogListSerializer
        return MedicationCatalogSerializer
    
    @swagger_auto_schema(
        responses={
            200: MedicationCatalogListSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Search medications by name, code, or category"
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_medications(self, request):
        """
        Search for medications by name, code, brand, or category
        """
        query = request.query_params.get('q', '')
        category = request.query_params.get('category', '')
        is_controlled = request.query_params.get('is_controlled')
        requires_prescription = request.query_params.get('requires_prescription')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(brand_name__icontains=query)
            )
        
        if category:
            queryset = queryset.filter(category=category)
        
        if is_controlled is not None:
            is_controlled_bool = is_controlled.lower() == 'true'
            queryset = queryset.filter(is_controlled=is_controlled_bool)
        
        if requires_prescription is not None:
            requires_prescription_bool = requires_prescription.lower() == 'true'
            queryset = queryset.filter(requires_prescription=requires_prescription_bool)
        
        serializer = MedicationCatalogListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        responses={
            200: MedicationCatalogListSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Get medications by category"
    )
    @action(detail=False, methods=['get'], url_path='by-category')
    def get_by_category(self, request):
        """
        Get medications grouped by category
        """
        categories = MedicationCatalog.CATEGORY_CHOICES
        result = {}
        
        for category_code, category_name in categories:
            tests = self.get_queryset().filter(category=category_code)
            if tests.exists():
                result[category_name] = MedicationCatalogListSerializer(
                    tests, many=True
                ).data
        
        return Response(result)


# class PrescriptionViewSet(viewsets.ModelViewSet):
#     """
#     ViewSet for managing prescriptions
    
#     Provides CRUD operations for prescriptions and additional actions for:
#     - Refilling prescriptions
#     - Updating status
#     - Managing schedules
#     - Tracking adherence
#     """
    
#     queryset = Prescription.objects.all()
#     permission_classes = [IsDoctorOrPatient]
    
#     def get_queryset(self):
#         queryset = super().get_queryset()
#         user = self.request.user
        
#         if hasattr(user, 'profile'):
#             if hasattr(user.profile, 'patient_profile'):
#                 # Patient can see their own prescriptions
#                 return queryset.filter(patient_profile=user.profile.patient_profile)
#             elif hasattr(user.profile, 'doctor_profile'):
#                 # Doctor can see prescriptions they've written or for patients they've consulted
#                 doctor = user.profile.doctor_profile
#                 return queryset.filter(
#                     Q(doctor_profile=doctor) |
#                     Q(patient_profile__consultations__doctor_profile=doctor)
#                 ).distinct()
        
#         return queryset.none()
    
#     def get_serializer_class(self):
#         if self.action == 'list':
#             return PrescriptionListSerializer
#         elif self.action == 'create':
#             return PrescriptionCreateSerializer
#         elif self.action == 'retrieve':
#             return PrescriptionWithSchedulesSerializer
#         return PrescriptionSerializer
    
#     def perform_create(self, serializer):
#         """Set doctor_profile from request user"""
#         request = self.context.get('request')
#         if request and hasattr(request.user, 'profile'):
#             if hasattr(request.user.profile, 'doctor_profile'):
#                 prescription = serializer.save(
#                     doctor_profile=request.user.profile.doctor_profile
#                 )
#                 # Create schedules if provided
#                 schedules_data = request.data.get('schedules', [])
#                 for schedule_data in schedules_data:
#                     MedicationSchedule.objects.create(
#                         prescription=prescription,
#                         **schedule_data
#                     )
#             else:
#                 raise PermissionError("Only doctors can create prescriptions")
#         else:
#             raise PermissionError("Authentication required")
    
#     @swagger_auto_schema(
#         methods=['post'],
#         request_body=PrescriptionRefillSerializer,
#         responses={
#             200: PrescriptionSerializer(),
#             400: "Bad Request",
#             404: "Prescription not found",
#             409: "Cannot refill"
#         },
#         operation_description="Refill a prescription"
#     )
#     @action(detail=False, methods=['post'], url_path='refill')
#     def refill_prescription(self, request):
#         """
#         Refill a prescription
#         """
#         prescription_id = request.data.get('prescription_id')
        
#         if not prescription_id:
#             return Response(
#                 {"error": "prescription_id is required"},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
        
#         prescription = get_object_or_404(Prescription, id=prescription_id)
        
#         # Check permissions
#         if hasattr(request.user, 'profile'):
#             if hasattr(request.user.profile, 'patient_profile'):
#                 if prescription.patient_profile != request.user.profile.patient_profile:
#                     return Response(
#                         {"error": "You can only refill your own prescriptions"},
#                         status=status.HTTP_403_FORBIDDEN
#                     )
#             elif hasattr(request.user.profile, 'doctor_profile'):
#                 # Doctors can refill any prescription they can see
#                 pass
#             else:
#                 return Response(
#                     {"error": "Unauthorized"},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
        
#         if not prescription.can_refill():
#             return Response(
#                 {"error": "This prescription cannot be refilled"},
#                 status=status.HTTP_409_CONFLICT
#             )
        
#         prescription.use_refill()
#         serializer = PrescriptionSerializer(prescription)
#         return Response(serializer.data)
    
#     @swagger_auto_schema(
#         methods=['post'],
#         request_body=PrescriptionStatusUpdateSerializer,
#         responses={
#             200: PrescriptionSerializer(),
#             400: "Bad Request",
#             404: "Prescription not found",
#             409: "Invalid status transition"
#         },
#         operation_description="Update prescription status"
#     )
#     @action(detail=True, methods=['post'], url_path='update-status')
#     def update_status(self, request, pk=None):
#         """
#         Update the status of a prescription
#         """
#         prescription = self.get_object()
        
#         # Check permissions
#         if hasattr(request.user, 'profile'):
#             if hasattr(request.user.profile, 'doctor_profile'):
#                 if prescription.doctor_profile != request.user.profile.doctor_profile:
#                     return Response(
#                         {"error": "Only the prescribing doctor can update status"},
#                         status=status.HTTP_403_FORBIDDEN
#                     )
#             else:
#                 return Response(
#                     {"error": "Only doctors can update prescription status"},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
        
#         serializer = PrescriptionStatusUpdateSerializer(data=request.data)
#         if serializer.is_valid():
#             new_status = serializer.validated_data['status']
#             reason = serializer.validated_data.get('reason', '')
            
#             # Prevent invalid transitions
#             valid_transitions = {
#                 'active': ['suspended', 'cancelled', 'completed'],
#                 'suspended': ['active', 'cancelled'],
#                 'draft': ['active', 'cancelled'],
#                 'completed': [],
#                 'cancelled': [],
#                 'expired': []
#             }
            
#             if prescription.status not in valid_transitions:
#                 return Response(
#                     {"error": f"Invalid current status: {prescription.status}"},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
            
#             if new_status not in valid_transitions.get(prescription.status, []):
#                 return Response(
#                     {"error": f"Cannot transition from {prescription.status} to {new_status}"},
#                     status=status.HTTP_409_CONFLICT
#                 )
            
#             # Apply status change
#             if new_status == 'suspended':
#                 prescription.suspend()
#             elif new_status == 'cancelled':
#                 prescription.cancel(reason)
#             elif new_status == 'completed':
#                 prescription.complete()
#             elif new_status == 'active':
#                 prescription.resume()
#             else:
#                 prescription.status = new_status
#                 prescription.save()
            
#             result_serializer = PrescriptionSerializer(prescription)
#             return Response(result_serializer.data)
        
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#     @swagger_auto_schema(
#         methods=['post'],
#         request_body=MedicationScheduleSerializer,
#         responses={
#             201: MedicationScheduleSerializer(),
#             400: "Bad Request",
#             404: "Prescription not found"
#         },
#         operation_description="Add a schedule to a prescription"
#     )
#     @action(detail=True, methods=['post'], url_path='add-schedule')
#     def add_schedule(self, request, pk=None):
#         """
#         Add a medication schedule to a prescription
#         """
#         prescription = self.get_object()
        
#         # Check permissions
#         if hasattr(request.user, 'profile'):
#             if hasattr(request.user.profile, 'doctor_profile'):
#                 if prescription.doctor_profile != request.user.profile.doctor_profile:
#                     return Response(
#                         {"error": "Only the prescribing doctor can add schedules"},
#                         status=status.HTTP_403_FORBIDDEN
#                     )
#             else:
#                 return Response(
#                     {"error": "Only doctors can add schedules"},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
        
#         serializer = MedicationScheduleSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save(prescription=prescription)
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#     @swagger_auto_schema(
#         responses={
#             200: MedicationScheduleSerializer(many=True),
#             404: "Prescription not found"
#         },
#         operation_description="Get schedules for a prescription"
#     )
#     @action(detail=True, methods=['get'], url_path='schedules')
#     def get_schedules(self, request, pk=None):
#         """
#         Get all schedules for a prescription
#         """
#         prescription = self.get_object()
#         schedules = prescription.schedules.all()
#         serializer = MedicationScheduleSerializer(schedules, many=True)
#         return Response(serializer.data)
    
#     @swagger_auto_schema(
#         methods=['post'],
#         request_body=MedicationAdherenceSerializer,
#         responses={
#             201: MedicationAdherenceSerializer(),
#             400: "Bad Request",
#             404: "Prescription not found"
#         },
#         operation_description="Record medication adherence"
#     )
#     @action(detail=True, methods=['post'], url_path='record-adherence')
#     def record_adherence(self, request, pk=None):
#         """
#         Record medication adherence for a prescription
#         """
#         prescription = self.get_object()
        
#         # Check permissions - only patient can record their own adherence
#         if hasattr(request.user, 'profile'):
#             if hasattr(request.user.profile, 'patient_profile'):
#                 if prescription.patient_profile != request.user.profile.patient_profile:
#                     return Response(
#                         {"error": "You can only record adherence for your own prescriptions"},
#                         status=status.HTTP_403_FORBIDDEN
#                     )
#             else:
#                 return Response(
#                     {"error": "Only patients can record adherence"},
#                     status=status.HTTP_403_FORBIDDEN
#                 )
        
#         data = request.data.copy()
#         data['prescription'] = prescription.id
#         data['patient_profile'] = prescription.patient_profile.id
        
#         # Check if adherence record already exists for today
#         today = timezone.now().date()
#         existing = MedicationAdherence.objects.filter(
#             prescription=prescription,
#             date=today
#         ).first()
        
#         if existing:
#             # Update existing record
#             serializer = MedicationAdherenceSerializer(existing, data=data, partial=True)
#         else:
#             # Create new record
#             serializer = MedicationAdherenceSerializer(data=data)
        
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data, status=status.HTTP_201_CREATED)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
#     @swagger_auto_schema(
#         responses={
#             200: MedicationAdherenceStatsSerializer(),
#             404: "Prescription not found"
#         },
#         operation_description="Get adherence statistics for a prescription"
#     )
#     @action(detail=True, methods=['get'], url_path='adherence-stats')
#     def get_adherence_stats(self, request, pk=None):
#         """
#         Get adherence statistics for a prescription
#         """
#         prescription = self.get_object()
        
#         # Get last 30 days of adherence records
#         end_date = timezone.now().date()
#         start_date = end_date - timedelta(days=30)
        
#         records = prescription.adherence_records.filter(
#             date__gte=start_date,
#             date__lte=end_date
#         )
        
#         total_days = 30
#         days_taken = records.filter(taken=True).count()
#         adherence_rate = (days_taken / total_days) * 100 if total_days > 0 else 0
        
#         missed_days = records.filter(taken=False).values_list('date', flat=True)
#         side_effects = records.exclude(side_effects='').values_list('side_effects', flat=True)
        
#         stats_data = {
#             'total_days': total_days,
#             'days_taken': days_taken,
#             'adherence_rate': round(adherence_rate, 2),
#             'missed_days': list(missed_days),
#             'side_effects_reported': list(side_effects)
#         }
        
#         serializer = MedicationAdherenceStatsSerializer(stats_data)
#         return Response(serializer.data)
    
#     @swagger_auto_schema(
#         responses={
#             200: PrescriptionListSerializer(many=True),
#             400: "Bad Request"
#         },
#         operation_description="Get prescriptions by patient"
#     )
#     @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
#     def get_patient_prescriptions(self, request, patient_id=None):
#         """
#         Get all prescriptions for a specific patient
#         """
#         patient = get_object_or_404(PatientProfile, id=patient_id)
        
#         # Check permissions
#         user = request.user
#         if hasattr(user, 'profile'):
#             if hasattr(user.profile, 'patient_profile'):
#                 if user.profile.patient_profile != patient:
#                     return Response(
#                         {"error": "You can only view your own prescriptions"},
#                         status=status.HTTP_403_FORBIDDEN
#                     )
        
#         prescriptions = self.get_queryset().filter(patient_profile=patient)
#         serializer = PrescriptionListSerializer(prescriptions, many=True)
#         return Response(serializer.data)
    
#     @swagger_auto_schema(
#         responses={
#             200: PrescriptionListSerializer(many=True),
#             400: "Bad Request"
#         },
#         operation_description="Get active prescriptions"
#     )
#     @action(detail=False, methods=['get'], url_path='active')
#     def get_active_prescriptions(self, request):
#         """
#         Get all active prescriptions
#         """
#         prescriptions = self.get_queryset().filter(status='active')
#         serializer = PrescriptionListSerializer(prescriptions, many=True)
#         return Response(serializer.data)
    
#     @swagger_auto_schema(
#         responses={
#             200: PrescriptionListSerializer(many=True),
#             400: "Bad Request"
#         },
#         operation_description="Get prescriptions needing refill"
#     )
#     @action(detail=False, methods=['get'], url_path='needing-refill')
#     def get_needing_refill(self, request):
#         """
#         Get prescriptions that need refill (low refills or expired soon)
#         """
#         queryset = self.get_queryset().filter(status='active')
        
#         # Filter prescriptions with low refills or expiring soon
#         low_refills = queryset.filter(refills_used__gte=0, refills__gt=0)  # We'll filter in code
        
#         result = []
#         for prescription in queryset:
#             if prescription.can_refill():
#                 # Check if refills are low (less than 2 remaining)
#                 remaining_refills = prescription.refills - prescription.refills_used
#                 if remaining_refills <= 2:
#                     result.append(prescription)
#                 # Check if expiring soon (within 7 days)
#                 elif prescription.expiry_date:
#                     days_until_expiry = (prescription.expiry_date - timezone.now().date()).days
#                     if 0 <= days_until_expiry <= 7:
#                         result.append(prescription)
        
#         serializer = PrescriptionListSerializer(result, many=True)
#         return Response(serializer.data)


class RefillRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing refill requests
    
    Provides CRUD operations for refill requests and actions for approving/rejecting
    """
    
    queryset = RefillRequest.objects.all()
    permission_classes = [IsDoctorOrPatient]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile'):
                # Patient can see their own refill requests
                return queryset.filter(patient_profile=user.profile.patient_profile)
            elif hasattr(user.profile, 'doctor_profile'):
                # Doctor can see refill requests for their patients
                doctor = user.profile.doctor_profile
                return queryset.filter(
                    prescription__doctor_profile=doctor
                ).distinct()
        
        return queryset.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RefillRequestCreateSerializer
        return RefillRequestSerializer
    
    def perform_create(self, serializer):
        """Set patient_profile from request user"""
        request = self.context.get('request')
        if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'patient_profile'):
            serializer.save(patient_profile=request.user.profile.patient_profile)
        else:
            raise PermissionError("Only patients can create refill requests")
    
    @swagger_auto_schema(
        methods=['post'],
        request_body=RefillRequestApproveSerializer,
        responses={
            200: RefillRequestSerializer(),
            400: "Bad Request",
            404: "Request not found",
            409: "Already processed"
        },
        operation_description="Approve or reject a refill request"
    )
    @action(detail=True, methods=['post'], url_path='review')
    def review_request(self, request, pk=None):
        """
        Review and approve/reject a refill request
        """
        refill_request = self.get_object()
        
        # Check permissions - only doctors can review
        if not hasattr(request.user, 'profile') or not hasattr(request.user.profile, 'doctor_profile'):
            return Response(
                {"error": "Only doctors can review refill requests"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if refill_request.status != 'pending':
            return Response(
                {"error": f"This request has already been {refill_request.status}"},
                status=status.HTTP_409_CONFLICT
            )
        
        serializer = RefillRequestApproveSerializer(data=request.data)
        if serializer.is_valid():
            approved = serializer.validated_data['approved']
            review_notes = serializer.validated_data.get('review_notes', '')
            
            doctor = request.user.profile.doctor_profile
            
            if approved:
                refill_request.approve(doctor)
                # Add review notes
                if review_notes:
                    refill_request.review_notes = review_notes
                    refill_request.save()
                message = "Refill request approved"
            else:
                refill_request.reject(doctor, review_notes)
                message = "Refill request rejected"
            
            result_serializer = RefillRequestSerializer(refill_request)
            return Response({
                'message': message,
                'data': result_serializer.data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        responses={
            200: RefillRequestSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Get pending refill requests"
    )
    @action(detail=False, methods=['get'], url_path='pending')
    def get_pending_requests(self, request):
        """
        Get all pending refill requests
        """
        requests = self.get_queryset().filter(status='pending')
        serializer = RefillRequestSerializer(requests, many=True)
        return Response(serializer.data)


class MedicationInteractionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing medication interactions
    
    Provides read-only access to drug-drug interactions
    """
    
    queryset = MedicationInteraction.objects.all()
    serializer_class = MedicationInteractionSerializer
    permission_classes = [IsDoctor]
    
    @swagger_auto_schema(
        responses={
            200: MedicationInteractionSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Check interactions for a medication"
    )
    @action(detail=False, methods=['get'], url_path='check/(?P<medication_id>[^/.]+)')
    def check_interactions(self, request, medication_id=None):
        """
        Check interactions for a specific medication
        """
        medication = get_object_or_404(MedicationCatalog, id=medication_id)
        
        interactions = self.get_queryset().filter(
            Q(medication_a=medication) | Q(medication_b=medication)
        )
        
        serializer = MedicationInteractionSerializer(interactions, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        methods=['post'],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'medication_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_INTEGER),
                    description='List of medication IDs to check'
                )
            },
            required=['medication_ids']
        ),
        responses={
            200: MedicationInteractionSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Check interactions between multiple medications"
    )
    @action(detail=False, methods=['post'], url_path='check-multiple')
    def check_multiple_interactions(self, request):
        """
        Check interactions between multiple medications
        """
        medication_ids = request.data.get('medication_ids', [])
        
        if not medication_ids or len(medication_ids) < 2:
            return Response(
                {"error": "At least 2 medication IDs are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        interactions = []
        for i in range(len(medication_ids)):
            for j in range(i + 1, len(medication_ids)):
                med_a = get_object_or_404(MedicationCatalog, id=medication_ids[i])
                med_b = get_object_or_404(MedicationCatalog, id=medication_ids[j])
                
                # Check both directions
                interaction = self.get_queryset().filter(
                    Q(medication_a=med_a, medication_b=med_b) |
                    Q(medication_a=med_b, medication_b=med_a)
                ).first()
                
                if interaction:
                    interactions.append(interaction)
        
        serializer = MedicationInteractionSerializer(interactions, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        responses={
            200: MedicationInteractionSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Get interactions by severity"
    )
    @action(detail=False, methods=['get'], url_path='by-severity/(?P<severity>[^/.]+)')
    def get_by_severity(self, request, severity=None):
        """
        Get interactions by severity level
        """
        valid_severities = [choice[0] for choice in MedicationInteraction.SEVERITY_CHOICES]
        if severity not in valid_severities:
            return Response(
                {"error": f"Invalid severity. Must be one of: {', '.join(valid_severities)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        interactions = self.get_queryset().filter(severity=severity)
        serializer = MedicationInteractionSerializer(interactions, many=True)
        return Response(serializer.data)


class MedicationAdherenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing medication adherence records
    
    Provides CRUD operations for adherence tracking
    """
    
    queryset = MedicationAdherence.objects.all()
    serializer_class = MedicationAdherenceSerializer
    permission_classes = [IsDoctorOrPatient]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile'):
                # Patient can see their own adherence records
                return queryset.filter(patient_profile=user.profile.patient_profile)
            elif hasattr(user.profile, 'doctor_profile'):
                # Doctor can see adherence records for their patients
                doctor = user.profile.doctor_profile
                return queryset.filter(
                    Q(prescription__doctor_profile=doctor) |
                    Q(patient_profile__consultations__doctor_profile=doctor)
                ).distinct()
        
        return queryset.none()
    
    @swagger_auto_schema(
        responses={
            200: MedicationAdherenceSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Get adherence records for a patient"
    )
    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
    def get_patient_adherence(self, request, patient_id=None):
        """
        Get adherence records for a specific patient
        """
        patient = get_object_or_404(PatientProfile, id=patient_id)
        
        # Check permissions
        user = request.user
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile'):
                if user.profile.patient_profile != patient:
                    return Response(
                        {"error": "You can only view your own adherence records"},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        records = self.get_queryset().filter(patient_profile=patient)
        serializer = MedicationAdherenceSerializer(records, many=True)
        return Response(serializer.data)
    
    
# apps/prescriptions/viewsets.py
from .serializers import (
    PrescriptionSerializer,
    PrescriptionListSerializer,
    PrescriptionCreateSerializer,   # ✅ our new one
    # ...other imports
)

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Prescription
from .serializers import PrescriptionSerializer, PrescriptionCreateSerializer
from accounts.models import Profile
from accounts.permissions import IsDoctor, IsDoctorOrPatient


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all()
    permission_classes = [IsDoctorOrPatient]

    def get_serializer_class(self):
        if self.action == 'create':
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not hasattr(user, 'profile'):
            return qs.none()

        if hasattr(user.profile, 'patient_profile'):
            return qs.filter(patient_profile=user.profile.patient_profile)
        if hasattr(user.profile, 'doctor_profile'):
            return qs.filter(doctor_profile=user.profile.doctor_profile)
        if user.is_staff:
            return qs
        return qs.none()

    def create(self, request, *args, **kwargs):
        """Create a prescription using mh_user_id"""
        serializer = PrescriptionCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        prescription = serializer.save()
        return Response(
            PrescriptionSerializer(prescription).data,
            status=status.HTTP_201_CREATED,
        )

    # ==========================================
    # FETCH by mh_user_id
    # ==========================================
    @swagger_auto_schema(
        operation_description="Get prescriptions by mh_user_id",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={200: PrescriptionSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def get_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response(
                {'error': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            return Response(
                {'error': f"Profile '{mh_user_id}' not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        patient_profile = getattr(profile, 'patient_profile', None)
        if not patient_profile:
            return Response(
                {'error': 'Patient profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        qs = Prescription.objects.filter(
            patient_profile=patient_profile
        ).order_by('-prescribed_date')

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': qs.count(),
            'data': PrescriptionSerializer(qs, many=True).data,
        })

    # ==========================================
    # Refill by mh_user_id
    # ==========================================
    @swagger_auto_schema(
        operation_description="Refill a prescription (by prescription_number)",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'prescription_number': openapi.Schema(
                    type=openapi.TYPE_STRING, description='e.g. RX-2026-0001'
                ),
            },
            required=['prescription_number']
        ),
        responses={200: PrescriptionSerializer()}
    )
    @action(detail=False, methods=['post'], url_path='refill')
    def refill(self, request):
        number = request.data.get('prescription_number')
        if not number:
            return Response(
                {'error': 'prescription_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            prescription = Prescription.objects.get(prescription_number=number)
        except Prescription.DoesNotExist:
            return Response(
                {'error': 'Prescription not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        if not prescription.can_refill():
            return Response(
                {'error': 'This prescription cannot be refilled'},
                status=status.HTTP_400_BAD_REQUEST
            )

        prescription.use_refill()
        return Response(PrescriptionSerializer(prescription).data)

    # ==========================================
    # Cancel by prescription_number
    # ==========================================
    @swagger_auto_schema(
        operation_description="Cancel a prescription",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'prescription_number': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['prescription_number']
        ),
        responses={200: PrescriptionSerializer()}
    )
    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request):
        number = request.data.get('prescription_number')
        if not number:
            return Response(
                {'error': 'prescription_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            prescription = Prescription.objects.get(prescription_number=number)
        except Prescription.DoesNotExist:
            return Response(
                {'error': 'Prescription not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        prescription.cancel()
        return Response(PrescriptionSerializer(prescription).data)