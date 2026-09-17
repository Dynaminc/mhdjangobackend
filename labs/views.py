# apps/labs/viewsets.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import (
    LabTestCatalog,
    LabTestOrder,
    LabTestResult,
    LabTestAttachment,
    LabPanel,
    LabTestProfile,
    LabOrderTemplate
)
from .serializers import (
    LabTestCatalogSerializer,
    LabTestCatalogListSerializer,
    LabTestOrderSerializer,
    LabTestOrderListSerializer,
    LabTestOrderCreateSerializer,
    LabTestAttachmentSerializer,
    LabPanelSerializer,
    LabTestProfileSerializer,
    LabOrderTemplateSerializer,
    LabResultVerifySerializer,
    LabOrderCancelSerializer
)
# from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrPatient
from accounts.models import PatientProfile


class LabTestCatalogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing lab test catalog
    
    Provides CRUD operations for the master list of available lab tests
    """
    
    queryset = LabTestCatalog.objects.filter(is_active=True)
    # permission_classes = [IsDoctor]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LabTestCatalogListSerializer
        return LabTestCatalogSerializer
    
    @swagger_auto_schema(
        responses={
            200: LabTestCatalogSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Search lab tests by name, code, or category"
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_tests(self, request):
        """
        Search for lab tests by name, code, or category
        """
        query = request.query_params.get('q', '')
        category = request.query_params.get('category', '')
        
        queryset = self.get_queryset()
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query) |
                Q(short_name__icontains=query)
            )
        
        if category:
            queryset = queryset.filter(category=category)
        
        serializer = LabTestCatalogListSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        responses={
            200: LabTestCatalogSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Get lab tests by category"
    )
    @action(detail=False, methods=['get'], url_path='by-category')
    def get_by_category(self, request):
        """
        Get lab tests grouped by category
        """
        categories = LabTestCatalog.CATEGORY_CHOICES
        result = {}
        
        for category_code, category_name in categories:
            tests = self.get_queryset().filter(category=category_code)
            if tests.exists():
                result[category_name] = LabTestCatalogListSerializer(
                    tests, many=True
                ).data
        
        return Response(result)


# apps/labs/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import LabTestOrder
from .serializers import LabTestOrderSerializer, LabTestOrderCreateSerializer
from accounts.models import Profile
from accounts.permissions import IsDoctor, IsDoctorOrPatient


class LabTestOrderViewSet(viewsets.ModelViewSet):
    queryset = LabTestOrder.objects.all()
    permission_classes = [IsDoctorOrPatient]

    def get_serializer_class(self):
        if self.action == 'create':
            return LabTestOrderCreateSerializer
        return LabTestOrderSerializer

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
        """Create a lab test order using mh_user_id"""
        serializer = LabTestOrderCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            LabTestOrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    # ==========================================
    # FETCH by mh_user_id
    # ==========================================
    @swagger_auto_schema(
        operation_description="Get lab orders by mh_user_id",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={200: LabTestOrderSerializer(many=True)}
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

        qs = LabTestOrder.objects.filter(
            patient_profile=patient_profile
        ).order_by('-ordered_date')

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': qs.count(),
            'data': LabTestOrderSerializer(qs, many=True).data,
        })

    # ==========================================
    # Cancel by order_number
    # ==========================================
    @swagger_auto_schema(
        operation_description="Cancel a lab order",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'order_number': openapi.Schema(
                    type=openapi.TYPE_STRING, description='e.g. LAB-2026-0001'
                ),
            },
            required=['order_number']
        ),
        responses={200: LabTestOrderSerializer()}
    )
    @action(detail=False, methods=['post'], url_path='cancel')
    def cancel(self, request):
        number = request.data.get('order_number')
        if not number:
            return Response(
                {'error': 'order_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = LabTestOrder.objects.get(order_number=number)
        except LabTestOrder.DoesNotExist:
            return Response(
                {'error': 'Lab order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        order.cancel()
        return Response(LabTestOrderSerializer(order).data)

    # ==========================================
    # Complete with results
    # ==========================================
    @swagger_auto_schema(
        operation_description="Mark a lab order as completed with results",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'order_number': openapi.Schema(type=openapi.TYPE_STRING),
                'result_value': openapi.Schema(type=openapi.TYPE_STRING),
                'result_notes': openapi.Schema(type=openapi.TYPE_STRING),
                'is_abnormal': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
            required=['order_number']
        ),
        responses={200: LabTestOrderSerializer()}
    )
    @action(detail=False, methods=['post'], url_path='complete')
    def complete(self, request):
        number = request.data.get('order_number')
        if not number:
            return Response(
                {'error': 'order_number is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            order = LabTestOrder.objects.get(order_number=number)
        except LabTestOrder.DoesNotExist:
            return Response(
                {'error': 'Lab order not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        order.result_value = request.data.get('result_value', '')
        order.result_notes = request.data.get('result_notes', '')
        order.is_abnormal = request.data.get('is_abnormal', False)
        order.complete()
        return Response(LabTestOrderSerializer(order).data)
    



class LabPanelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing lab panels
    
    Provides CRUD operations for pre-defined panels of tests
    """
    
    queryset = LabPanel.objects.filter(is_active=True)
    serializer_class = LabPanelSerializer
    # permission_classes = [IsDoctor]
    
    @swagger_auto_schema(
        responses={
            200: LabPanelSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Search lab panels"
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_panels(self, request):
        """
        Search for lab panels by name or code
        """
        query = request.query_params.get('q', '')
        
        queryset = self.get_queryset()
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(code__icontains=query)
            )
        
        serializer = LabPanelSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        methods=['post'],
        responses={
            201: LabTestOrderSerializer(),
            400: "Bad Request"
        },
        operation_description="Create order from panel"
    )
    @action(detail=True, methods=['post'], url_path='create-order')
    def create_order_from_panel(self, request, pk=None):
        """
        Create a lab order from a panel
        """
        panel = self.get_object()
        patient_id = request.data.get('patient_profile_id')
        consultation_id = request.data.get('consultation_id')
        medical_record_id = request.data.get('medical_record_id')
        
        if not patient_id:
            return Response(
                {"error": "patient_profile_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        patient = get_object_or_404(PatientProfile, id=patient_id)
        
        # Create an order for each test in the panel
        orders = []
        for test in panel.tests.all():
            order_data = {
                'test_catalog': test,
                'patient_profile': patient,
                'medical_record_id': medical_record_id,
                'consultation_id': consultation_id,
                'priority': request.data.get('priority', 'routine'),
                'clinical_notes': request.data.get('clinical_notes', ''),
                'clinical_indication': f"Panel: {panel.name}"
            }
            
            order_serializer = LabTestOrderCreateSerializer(
                data=order_data,
                context={'request': request}
            )
            
            if order_serializer.is_valid():
                order = order_serializer.save()
                orders.append(order)
            else:
                return Response(
                    {"error": f"Failed to create order for test {test.name}",
                     "details": order_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Return all created orders
        order_serializer = LabTestOrderListSerializer(orders, many=True)
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)


class LabTestProfileViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing lab test profiles
    
    Provides read-only access to patient-specific lab test profiles and trending
    """
    
    queryset = LabTestProfile.objects.all()
    serializer_class = LabTestProfileSerializer
    # permission_classes = [IsDoctorOrPatient]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile'):
                # Patient can see their own profiles
                return queryset.filter(patient_profile=user.profile.patient_profile)
            elif hasattr(user.profile, 'doctor_profile'):
                # Doctor can see profiles for patients they've consulted
                doctor = user.profile.doctor_profile
                return queryset.filter(
                    patient_profile__consultations__doctor_profile=doctor
                ).distinct()
        
        return queryset.none()
    
    @swagger_auto_schema(
        responses={
            200: LabTestProfileSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Get profiles for a patient"
    )
    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)')
    def get_patient_profiles(self, request, patient_id=None):
        """
        Get lab profiles for a specific patient
        """
        patient = get_object_or_404(PatientProfile, id=patient_id)
        
        # Check permissions
        user = request.user
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile'):
                if user.profile.patient_profile != patient:
                    return Response(
                        {"error": "You can only view your own lab profiles"},
                        status=status.HTTP_403_FORBIDDEN
                    )
        
        profiles = self.get_queryset().filter(patient_profile=patient)
        serializer = LabTestProfileSerializer(profiles, many=True)
        return Response(serializer.data)


class LabOrderTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing lab order templates
    
    Provides CRUD operations for pre-defined order templates
    """
    
    queryset = LabOrderTemplate.objects.all()
    serializer_class = LabOrderTemplateSerializer
    # permission_classes = [IsDoctor]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile') and hasattr(user.profile, 'doctor_profile'):
            doctor = user.profile.doctor_profile
            # Show public templates and user's own templates
            return queryset.filter(
                Q(is_public=True) |
                Q(created_by=doctor)
            ).distinct()
        
        return queryset.none()
    
    def perform_create(self, serializer):
        """Set created_by to current doctor"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            if hasattr(request.user.profile, 'doctor_profile'):
                serializer.save(created_by=request.user.profile.doctor_profile)
    
    @swagger_auto_schema(
        responses={
            200: LabOrderTemplateSerializer(many=True),
            400: "Bad Request"
        },
        operation_description="Search lab templates"
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_templates(self, request):
        """
        Search for templates by name
        """
        query = request.query_params.get('q', '')
        
        queryset = self.get_queryset()
        if query:
            queryset = queryset.filter(name__icontains=query)
        
        serializer = LabOrderTemplateSerializer(queryset, many=True)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        methods=['post'],
        responses={
            201: LabTestOrderSerializer(),
            400: "Bad Request"
        },
        operation_description="Create order from template"
    )
    @action(detail=True, methods=['post'], url_path='create-order')
    def create_order_from_template(self, request, pk=None):
        """
        Create a lab order from a template
        """
        template = self.get_object()
        patient_id = request.data.get('patient_profile_id')
        consultation_id = request.data.get('consultation_id')
        medical_record_id = request.data.get('medical_record_id')
        
        if not patient_id:
            return Response(
                {"error": "patient_profile_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        patient = get_object_or_404(PatientProfile, id=patient_id)
        
        # Increment usage count
        template.usage_count += 1
        template.save()
        
        # Create an order for each test in the template
        orders = []
        for test in template.tests.all():
            order_data = {
                'test_catalog': test,
                'patient_profile': patient,
                'medical_record_id': medical_record_id,
                'consultation_id': consultation_id,
                'priority': request.data.get('priority', 'routine'),
                'clinical_notes': request.data.get('clinical_notes', ''),
                'clinical_indication': request.data.get(
                    'clinical_indication',
                    f"Template: {template.name}"
                )
            }
            
            order_serializer = LabTestOrderCreateSerializer(
                data=order_data,
                context={'request': request}
            )
            
            if order_serializer.is_valid():
                order = order_serializer.save()
                orders.append(order)
            else:
                return Response(
                    {"error": f"Failed to create order for test {test.name}",
                     "details": order_serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Return all created orders
        order_serializer = LabTestOrderListSerializer(orders, many=True)
        return Response(order_serializer.data, status=status.HTTP_201_CREATED)