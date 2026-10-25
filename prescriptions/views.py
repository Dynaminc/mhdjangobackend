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
    # RefillRequest,
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
    # RefillRequestSerializer,
    # RefillRequestCreateSerializer,
    # RefillRequestApproveSerializer,
    MedicationInteractionSerializer,
    MedicationScheduleSerializer,
    MedicationAdherenceSerializer,
    MedicationAdherenceStatsSerializer,
    MedicationSearchSerializer
)
from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrPatient, IsAdmin
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

# apps/prescriptions/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.db import transaction


from .models import Prescription
from .serializers import PrescriptionSerializer, PrescriptionCreateSerializer
from accounts.models import Profile
from accounts.permissions import IsDoctorOrPatient


class PrescriptionViewSet(viewsets.ModelViewSet):
    queryset = Prescription.objects.all()
    permission_classes = [IsDoctorOrPatient | IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return PrescriptionCreateSerializer
        return PrescriptionSerializer

    def get_queryset(self):
        qs = super().get_queryset().order_by('-created_at')
        user = self.request.user
        profile = getattr(user, 'profile', None)

        if profile is None:
            return qs.none()
        if user.is_staff:
            return qs
        if profile.role == 'doctor':
            dp = getattr(profile, 'doctor_profile', None)
            return qs.filter(doctor_profile=dp) if dp else qs.none()
        if profile.role == 'patient':
            pp = getattr(profile, 'patient_profile', None)
            return qs.filter(patient_profile=pp) if pp else qs.none()
        return qs.none()

    def create(self, request, *args, **kwargs):
        serializer = PrescriptionCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        prescription = serializer.save()
        return Response(
            PrescriptionSerializer(prescription).data,
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_description="Get prescriptions by mh_user_id",
        manual_parameters=[
            openapi.Parameter('mh_user_id', openapi.IN_QUERY,
                              type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: PrescriptionSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def get_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response(
                {'error': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = Prescription.objects.filter(
            patient_profile__profile__mh_user_id=mh_user_id
        ).order_by('-created_at')

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': qs.count(),
            'data': PrescriptionSerializer(qs, many=True).data,
        })
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._assert_can_modify(request.user, instance)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        self._assert_can_modify(request.user, instance)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._assert_can_modify(request.user, instance)
        return super().destroy(request, *args, **kwargs)

    def _assert_can_modify(self, user, instance):
        from rest_framework.exceptions import PermissionDenied
        profile = getattr(user, 'profile', None)
        if user.is_staff:
            return
        if profile is None or profile.role != 'doctor':
            raise PermissionDenied('Only the prescribing doctor can modify this item.')
        doctor = getattr(profile, 'doctor_profile', None)
        if not doctor or instance.doctor_profile_id != doctor.id:
            raise PermissionDenied('Only the prescribing doctor can modify this item.')        

    @swagger_auto_schema(
        operation_description="Replace the entire prescription list for a consultation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mh_user_id': openapi.Schema(type=openapi.TYPE_STRING),
                'consultation_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                'items': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'name': openapi.Schema(type=openapi.TYPE_STRING),
                            'instructions': openapi.Schema(type=openapi.TYPE_STRING),
                            'quantity': openapi.Schema(type=openapi.TYPE_INTEGER),
                        },
                    ),
                ),
            },
            required=['mh_user_id', 'items'],
        ),
        responses={200: PrescriptionSerializer(many=True)},
    )
    @action(detail=False, methods=['post'], url_path='replace-list')
    def replace_list(self, request):
        mh_user_id = request.data.get('mh_user_id')
        consultation_id = request.data.get('consultation_id')
        items = request.data.get('items', [])

        # Resolve patient
        from accounts.models import Profile, PatientProfile
        from consultations.models import Consultation
        from rest_framework.exceptions import ValidationError, PermissionDenied

        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            raise ValidationError({'mh_user_id': 'not found'})
        patient_profile = getattr(profile, 'patient_profile', None)
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)

        # Doctor
        doctor = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor:
            raise PermissionDenied('Only doctors can modify prescriptions.')

        # Consultation
        consultation = None
        if consultation_id:
            try:
                consultation = Consultation.objects.get(id=consultation_id)
            except Consultation.DoesNotExist:
                raise ValidationError({'consultation_id': 'not found'})
            if consultation.patient_profile_id != patient_profile.id:
                raise ValidationError({'consultation_id': 'does not belong to this patient'})

        with transaction.atomic():
            # Delete existing items for this consultation + doctor + patient
            qs = Prescription.objects.filter(
                patient_profile=patient_profile,
                doctor_profile=doctor,
            )
            if consultation:
                qs = qs.filter(consultation=consultation)
            else:
                qs = qs.filter(consultation__isnull=True)
            qs.delete()

            # Recreate from payload
            created = [
                Prescription.objects.create(
                    consultation=consultation,
                    patient_profile=patient_profile,
                    doctor_profile=doctor,
                    name=item.get('name', '').strip(),
                    instructions=item.get('instructions', ''),
                    quantity=item.get('quantity', 1),
                )
                for item in items
                if item.get('name')
            ]

        return Response({
            'status': 'success',
            'count': len(created),
            'data': PrescriptionSerializer(created, many=True).data,
        })        
