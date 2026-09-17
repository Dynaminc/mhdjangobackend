from django.shortcuts import render

# Create your views here.
# apps/consultations/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from consultations.models import Consultation
from .serializers import  *
import requests
from django.conf import settings

class CompleteConsultationView(APIView):
    """Complete a consultation and archive the chat"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        consultation_id = request.data.get('consultation_id')
        conversation_id = request.data.get('conversation_id')
        ended_at = request.data.get('ended_at')
        
        try:
            consultation = Consultation.objects.get(id=consultation_id)
            
            # Only doctor or patient can complete
            if request.user.id != consultation.doctor.user_id and \
               request.user.id != consultation.patient.user_id:
                return Response({'error': 'Unauthorized'}, status=403)
            
            # Update consultation status
            consultation.status = 'completed'
            consultation.save()
            
            # Notify chat server to archive conversation
            if conversation_id:
                requests.post(
                    f"{settings.CHAT_SERVER_URL}/api/chat/conversations/{conversation_id}/archive",
                    json={'ended_at': ended_at},
                    headers={'Authorization': f'Bearer {settings.CHAT_API_KEY}'}
                )
            
            return Response({
                'status': 'success',
                'consultation_id': consultation.id,
                'ended_at': ended_at
            })
            
        except Consultation.DoesNotExist:
            return Response({'error': 'Consultation not found'}, status=404)
        
        
        
# apps/consultations/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Consultation, Examination
from .serializers import (
    ConsultationSerializer,
    ConsultationCreateSerializer,
    ExaminationSerializer,
    PastMedicalHistorySerializer,
)
from appointments.models import Appointment
from accounts.models import Profile, PatientProfile, DoctorProfile
from accounts.permissions import IsDoctor, IsDoctorOrPatient


class ConsultationViewSet(viewsets.ModelViewSet):
    """
    Consultation management — driven by `mh_user_id`.

    - CREATE: POST /consultations/ with mh_user_id (+ optional doctor_id)
              or with appointment_id to inherit patient + doctor.
    - FETCH:  GET /consultations/by-mh-user-id/?mh_user_id=MH-XXXX
    - COMPLETE: POST /consultations/complete-by-mh-user-id/
    - ADD EXAM: POST /consultations/{id}/add-examination/
    - PATIENT HISTORY: GET /consultations/patient-history/?mh_user_id=MH-XXXX
    """

    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsDoctorOrPatient]

    # =====================================================
    # SERIALIZER SELECTION
    # =====================================================
    def get_serializer_class(self):
        if self.action in ['create', 'create_from_appointment']:
            return ConsultationCreateSerializer
        return ConsultationSerializer

    # =====================================================
    # QUERYSET
    # =====================================================
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not hasattr(user, 'profile'):
            return queryset.none()

        if hasattr(user.profile, 'patient_profile'):
            return queryset.filter(patient_profile=user.profile.patient_profile)

        if hasattr(user.profile, 'doctor_profile'):
            return queryset.filter(doctor_profile=user.profile.doctor_profile)

        if user.is_staff:
            return queryset
        return queryset.none()

    # =====================================================
    # PERMISSIONS
    # =====================================================
    def get_permissions(self):
        if self.action in [
            'create',
            'create_from_appointment',
            'complete_by_mh_user_id',
            'update',
            'partial_update',
            'destroy',
            'add_examination',
            'link_chat',
        ]:
            self.permission_classes = [IsDoctor]
        else:
            self.permission_classes = [IsDoctorOrPatient]
        return [p() for p in self.permission_classes]

    # =====================================================
    # HELPER — mh_user_id → PatientProfile (auto-create)
    # =====================================================
    def _resolve_patient_profile(self, mh_user_id):
        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            return None, f"Profile with mh_user_id '{mh_user_id}' not found"

        patient_profile = getattr(profile, 'patient_profile', None)
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)
        return patient_profile, None

    # =====================================================
    # CREATE (uses mh_user_id or appointment_id)
    # =====================================================
    @swagger_auto_schema(
        operation_description=(
            "Create a consultation. "
            "Send either `mh_user_id` (+ optional `doctor_id`) "
            "OR `appointment_id` to inherit patient & doctor."
        ),
        request_body=ConsultationCreateSerializer,
        responses={
            201: ConsultationSerializer(),
            400: "Bad Request",
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = ConsultationCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        consultation = serializer.save()
        return Response(
            ConsultationSerializer(consultation).data,
            status=status.HTTP_201_CREATED,
        )

    # =====================================================
    # CREATE FROM APPOINTMENT (dedicated endpoint)
    # =====================================================
    @swagger_auto_schema(
        operation_description="Create a consultation from an existing appointment",
        request_body=ConsultationCreateSerializer,
        responses={
            201: ConsultationSerializer(),
            400: "Bad Request",
        }
    )
    @action(detail=False, methods=['post'], url_path='create-from-appointment')
    def create_from_appointment(self, request):
        serializer = ConsultationCreateSerializer(
            data=request.data, context={'request': request}
        )
        if serializer.is_valid():
            consultation = serializer.save()
            return Response(
                ConsultationSerializer(consultation).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =====================================================
    # FETCH by mh_user_id
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get consultations by mh_user_id",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id (e.g., MH-2026-1358F4D6)",
                type=openapi.TYPE_STRING, required=True,
            )
        ],
        responses={200: ConsultationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def get_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response(
                {'status': 'error', 'message': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response(
                {'status': 'error', 'message': error},
                status=status.HTTP_404_NOT_FOUND,
            )

        consultations = Consultation.objects.filter(
            patient_profile=patient_profile
        ).order_by('-created_at')
        serializer = ConsultationSerializer(consultations, many=True)

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'patient_profile_id': patient_profile.id,
            'count': consultations.count(),
            'data': serializer.data,
        })

    # =====================================================
    # COMPLETE by mh_user_id
    # =====================================================
    @swagger_auto_schema(
        operation_description="Complete a consultation by mh_user_id",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mh_user_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Patient mh_user_id'
                ),
                'consultation_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description='Optional — target a specific consultation'
                ),
            },
            required=['mh_user_id'],
        ),
        responses={
            200: ConsultationSerializer(),
            400: "Bad Request",
            403: "Forbidden",
            404: "Not found",
        }
    )
    @action(detail=False, methods=['post'], url_path='complete-by-mh-user-id')
    def complete_by_mh_user_id(self, request):
        mh_user_id = request.data.get('mh_user_id')
        consultation_id = request.data.get('consultation_id')

        if not mh_user_id:
            return Response(
                {'error': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response({'error': error}, status=status.HTTP_404_NOT_FOUND)

        qs = patient_profile.consultations.filter(status='ongoing')
        if consultation_id:
            qs = qs.filter(id=consultation_id)
        consultation = qs.order_by('-created_at').first()

        if not consultation:
            return Response(
                {'error': 'No ongoing consultation found for this patient'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if (
            hasattr(request.user.profile, 'doctor_profile') and
            request.user.profile.doctor_profile != consultation.doctor_profile
        ):
            return Response(
                {'error': 'Only the assigned doctor can complete this consultation'},
                status=status.HTTP_403_FORBIDDEN,
            )

        consultation.complete()
        return Response(self.get_serializer(consultation).data)

    # =====================================================
    # ADD EXAMINATION
    # =====================================================
    @swagger_auto_schema(
        operation_description="Add an examination to a consultation",
        request_body=ExaminationSerializer,
        responses={
            201: ExaminationSerializer(),
            400: "Bad Request",
            403: "Forbidden",
            404: "Not found",
        }
    )
    @action(detail=True, methods=['post'], url_path='add-examination')
    def add_examination(self, request, pk=None):
        consultation = self.get_object()

        if consultation.status != 'ongoing':
            return Response(
                {'error': 'Cannot add examinations to a completed/cancelled consultation'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            hasattr(request.user.profile, 'doctor_profile') and
            request.user.profile.doctor_profile != consultation.doctor_profile
        ):
            return Response(
                {'error': 'Only the assigned doctor can add examinations'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ExaminationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(consultation=consultation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # =====================================================
    # GET EXAMINATIONS
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get all examinations for a consultation",
        responses={200: ExaminationSerializer(many=True)}
    )
    @action(detail=True, methods=['get'], url_path='examinations')
    def get_examinations(self, request, pk=None):
        consultation = self.get_object()
        serializer = ExaminationSerializer(consultation.examinations.all(), many=True)
        return Response(serializer.data)

    # =====================================================
    # LINK CHAT
    # =====================================================
    @swagger_auto_schema(
        operation_description="Link a chat conversation to the consultation",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'chat_conversation_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Chat conversation ID from Flask chat server'
                ),
            },
            required=['chat_conversation_id'],
        ),
        responses={200: ConsultationSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='link-chat')
    def link_chat(self, request, pk=None):
        consultation = self.get_object()
        chat_id = request.data.get('chat_conversation_id')
        if not chat_id:
            return Response(
                {'error': 'chat_conversation_id required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        consultation.chat_conversation_id = chat_id
        consultation.save()
        return Response(self.get_serializer(consultation).data)

    # =====================================================
    # PATIENT HISTORY by mh_user_id
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get patient's past medical history by mh_user_id",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING, required=True,
            )
        ],
        responses={200: PastMedicalHistorySerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='patient-history')
    def get_patient_history(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response(
                {'error': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response({'error': error}, status=status.HTTP_404_NOT_FOUND)

        histories = patient_profile.past_medical_histories.filter(is_active=True)
        serializer = PastMedicalHistorySerializer(histories, many=True)

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': histories.count(),
            'data': serializer.data,
        })
                

class ExaminationViewSet(viewsets.ModelViewSet):
    """
    Examination management — supports `mh_user_id` for retrieval.
    """

    queryset = Examination.objects.all()
    serializer_class = ExaminationSerializer
    permission_classes = [IsDoctorOrPatient]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if not hasattr(user, 'profile'):
            return queryset.none()

        if hasattr(user.profile, 'doctor_profile'):
            return queryset.filter(consultation__doctor_profile=user.profile.doctor_profile)

        if hasattr(user.profile, 'patient_profile'):
            return queryset.filter(consultation__patient_profile=user.profile.patient_profile)

        if user.is_staff:
            return queryset
        return queryset.none()

    # =====================================================
    # Helper
    # =====================================================
    def _resolve_patient_profile(self, mh_user_id):
        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            return None, f"Profile with mh_user_id '{mh_user_id}' not found"

        patient_profile = getattr(profile, 'patient_profile', None)
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)
        return patient_profile, None

    # =====================================================
    # Get vitals by mh_user_id (across all consultations)
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get all vital examinations for a patient (by mh_user_id)",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={200: ExaminationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='vitals-by-mh-user-id')
    def vitals_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response({'error': 'mh_user_id is required'}, status=400)

        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response({'error': error}, status=404)

        vitals = Examination.objects.filter(
            consultation__patient_profile=patient_profile,
            examination_type='vitals'
        ).order_by('-created_at')

        serializer = self.get_serializer(vitals, many=True)
        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': vitals.count(),
            'data': serializer.data
        })

    # =====================================================
    # Get all examinations for a patient
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get all examinations for a patient (by mh_user_id)",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={200: ExaminationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response({'error': 'mh_user_id is required'}, status=400)

        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response({'error': error}, status=404)

        exams = Examination.objects.filter(
            consultation__patient_profile=patient_profile
        ).order_by('-created_at')

        serializer = self.get_serializer(exams, many=True)
        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': exams.count(),
            'data': serializer.data
        })

    # =====================================================
    # Existing: vitals by consultation_id (kept)
    # =====================================================
    @action(detail=False, methods=['get'], url_path='vitals/(?P<consultation_id>[^/.]+)')
    def get_vitals(self, request, consultation_id=None):
        consultation = get_object_or_404(Consultation, id=consultation_id)
        vitals = consultation.examinations.filter(examination_type='vitals')
        return Response(ExaminationSerializer(vitals, many=True).data)
    

# apps/consultations/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import PastMedicalHistory, MedicalRecord
from .serializers import PastMedicalHistorySerializer
from accounts.models import PatientProfile, Profile
from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrPatient
import uuid


# apps/consultations/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import PastMedicalHistory
from .serializers import PastMedicalHistorySerializer
from accounts.models import Profile, PatientProfile
from accounts.permissions import IsDoctor, IsPatient, IsDoctorOrPatient

# apps/consultations/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import PastMedicalHistory
from .serializers import PastMedicalHistorySerializer
from accounts.models import Profile, PatientProfile
from accounts.permissions import IsDoctor, IsDoctorOrPatient


class PastMedicalHistoryViewSet(viewsets.ModelViewSet):
    """
    Past Medical History — driven by `mh_user_id`.

    ALL operations (create / fetch) use `mh_user_id`.
    The view transparently resolves the underlying PatientProfile,
    creating one if it does not exist.
    """

    queryset = PastMedicalHistory.objects.all()
    serializer_class = PastMedicalHistorySerializer
    permission_classes = [IsDoctorOrPatient]

    # =====================================================
    # QUERYSET — patients see their own history
    # =====================================================
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if not hasattr(user, 'profile'):
            return queryset.none()

        if hasattr(user.profile, 'patient_profile'):
            return queryset.filter(patient_profile=user.profile.patient_profile)

        if hasattr(user.profile, 'doctor_profile'):
            doctor = user.profile.doctor_profile
            return queryset.filter(
                patient_profile__consultations__doctor_profile=doctor
            ).distinct()

        return queryset.none()

    # =====================================================
    # PERMISSIONS
    # =====================================================
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsDoctor]
        else:
            self.permission_classes = [IsDoctorOrPatient]
        return [permission() for permission in self.permission_classes]

    # =====================================================
    # HELPER: mh_user_id → PatientProfile (auto-create if missing)
    # =====================================================
    def _resolve_patient_profile(self, mh_user_id):
        """
        Given an mh_user_id, return the corresponding PatientProfile.
        If the Profile exists but has no PatientProfile, create one.
        Returns (patient_profile, error_message).
        """
        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            return None, f"Profile with mh_user_id '{mh_user_id}' not found"

        # Try to fetch existing PatientProfile
        patient_profile = getattr(profile, 'patient_profile', None)

        # Auto-create if missing
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)
            print(f"✅ PatientProfile auto-created for {mh_user_id}")

        return patient_profile, None

    # =====================================================
    # CREATE — expects `mh_user_id`
    # =====================================================
    @swagger_auto_schema(
        operation_description="Create a medical history entry using mh_user_id",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mh_user_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Patient mh_user_id (e.g., MH-2026-1358F4D6)'
                ),
                'history_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='e.g. general, surgical, allergy, medication'
                ),
                'content': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='The history content'
                ),
                'notes': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='Optional notes'
                ),
                'is_active': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description='Active flag (default: true)'
                ),
            },
            required=['mh_user_id', 'history_type', 'content']
        ),
        responses={201: PastMedicalHistorySerializer()}
    )
    def create(self, request, *args, **kwargs):
        mh_user_id = request.data.get('mh_user_id')

        if not mh_user_id:
            return Response({
                'status': 'error',
                'message': 'mh_user_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Resolve → get or create PatientProfile
        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response({
                'status': 'error',
                'message': error
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate history_type
        history_type = request.data.get('history_type')
        valid_types = [choice[0] for choice in PastMedicalHistory.HISTORY_TYPES]
        if history_type not in valid_types:
            return Response({
                'status': 'error',
                'message': (
                    f"Invalid history_type '{history_type}'. "
                    f"Valid choices are: {', '.join(valid_types)}"
                )
            }, status=status.HTTP_400_BAD_REQUEST)

        # Build serializer data — swap mh_user_id for patient_profile
        data = request.data.copy()
        data.pop('mh_user_id', None)                  # remove, no longer needed
        data['patient_profile'] = patient_profile.id  # set FK directly

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Attach the current doctor as recorder
        if hasattr(request.user.profile, 'doctor_profile'):
            serializer.validated_data['recorded_by'] = request.user.profile.doctor_profile

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    # =====================================================
    # FETCH by mh_user_id
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get medical history by mh_user_id",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id',
                openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={200: PastMedicalHistorySerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def get_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')

        if not mh_user_id:
            return Response({
                'status': 'error',
                'message': 'mh_user_id query parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return Response({
                'status': 'error',
                'message': error
            }, status=status.HTTP_404_NOT_FOUND)

        histories = patient_profile.past_medical_histories.filter(is_active=True)
        serializer = self.get_serializer(histories, many=True)

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'patient_profile_id': patient_profile.id,
            'count': histories.count(),
            'data': serializer.data
        })

    @swagger_auto_schema(
        operation_description="Update medical history by mh_user_id + history_type",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mh_user_id': openapi.Schema(type=openapi.TYPE_STRING),
                'history_type': openapi.Schema(type=openapi.TYPE_STRING),
                'content': openapi.Schema(type=openapi.TYPE_STRING),
                'notes': openapi.Schema(type=openapi.TYPE_STRING),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
            required=['mh_user_id', 'history_type']
        ),
        responses={200: PastMedicalHistorySerializer()}
    )
    @action(detail=False, methods=['post'], url_path='update-by-mh-user-id')
    def update_by_mh_user_id(self, request):
        mh_user_id = request.data.get('mh_user_id')
        history_type = request.data.get('history_type')

        if not mh_user_id or not history_type:
            return Response({
                'status': '_find_by_mh_user_iderror',
                'message': 'mh_user_id and history_type are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        obj, error = self._find_by_mh_user_id(mh_user_id, history_type)
        if error:
            return Response({
                'status': 'error',
                'message': error
            }, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'status': 'success',
            'message': 'Medical history updated',
            'data': serializer.data
        })

    # =====================================================
    # DELETE by mh_user_id
    # =====================================================
    @swagger_auto_schema(
        operation_description="Delete medical history by mh_user_id + history_type",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mh_user_id': openapi.Schema(type=openapi.TYPE_STRING),
                'history_type': openapi.Schema(type=openapi.TYPE_STRING),
            },
            required=['mh_user_id', 'history_type']
        ),
        responses={200: openapi.Response('Deleted')}
    )
    @action(detail=False, methods=['post'], url_path='delete-by-mh-user-id')
    def delete_by_mh_user_id(self, request):
        mh_user_id = request.data.get('mh_user_id')
        history_type = request.data.get('history_type')

        if not mh_user_id or not history_type:
            return Response({
                'status': 'error',
                'message': 'mh_user_id and history_type are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        obj, error = self._find_by_mh_user_id(mh_user_id, history_type)
        if error:
            return Response({
                'status': 'error',
                'message': error
            }, status=status.HTTP_404_NOT_FOUND)

        obj.delete()
        return Response({
            'status': 'success',
            'message': 'Medical history deleted'
        })

    # =====================================================
    # HISTORY TYPES
    # =====================================================
    @swagger_auto_schema(
        operation_description="Get history type choices",
        responses={200: openapi.Response('History types')}
    )
    @action(detail=False, methods=['get'], url_path='types')
    def get_history_types(self, request):
        types = [
            {'value': choice[0], 'label': choice[1]}
            for choice in PastMedicalHistory.HISTORY_TYPES
        ]
        return Response({
            'status': 'success',
            'data': types
        })    
    
    def _find_by_mh_user_id(self, mh_user_id, history_type=None):
        patient_profile, error = self._resolve_patient_profile(mh_user_id)
        if error:
            return None, error

        qs = PastMedicalHistory.objects.filter(patient_profile=patient_profile)
        if history_type:
            qs = qs.filter(history_type=history_type)

        obj = qs.order_by('-created_at').first()
        if not obj:
            return None, "PastMedicalHistory not found for this mh_user_id"
        return obj, None
    
class MedicalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing medical records
    
    Provides read-only access to comprehensive patient medical records
    """
    
    queryset = MedicalRecord.objects.all()
    serializer_class = MedicalRecordSerializer
    # permission_classes = [IsDoctorOrPatient]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile'):
                # Patient can see their own medical record
                return queryset.filter(patient_profile=user.profile.patient_profile)
            elif hasattr(user.profile, 'doctor_profile'):
                # Doctor can see records for patients they've consulted
                doctor = user.profile.doctor_profile
                return queryset.filter(patient_profile__consultations__doctor_profile=doctor).distinct()
        
        return queryset.none()
    
    @swagger_auto_schema(
        responses={
            200: PatientFullMedicalRecordSerializer(),
            404: "Patient not found"
        },
        operation_description="Get complete medical record for a patient"
    )
    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)/full')
    def get_full_record(self, request, patient_id=None):
        """
        Get the complete medical record for a patient
        """
        patient = get_object_or_404(PatientProfile, id=patient_id)
        
        # Check permissions
        user = request.user
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile') and user.profile.patient_profile != patient:
                return Response(
                    {"error": "You can only view your own medical record"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        full_record = get_patient_full_medical_record(patient)
        serializer = PatientFullMedicalRecordSerializer(full_record)
        return Response(serializer.data)
    
    @swagger_auto_schema(
        responses={
            200: ConsultationSerializer(many=True),
            404: "Patient not found"
        },
        operation_description="Get all consultations for a patient"
    )
    @action(detail=False, methods=['get'], url_path='patient/(?P<patient_id>[^/.]+)/consultations')
    def get_patient_consultations(self, request, patient_id=None):
        """
        Get all consultations for a patient
        """
        patient = get_object_or_404(PatientProfile, id=patient_id)
        
        # Check permissions
        user = request.user
        if hasattr(user, 'profile'):
            if hasattr(user.profile, 'patient_profile') and user.profile.patient_profile != patient:
                return Response(
                    {"error": "You can only view your own consultations"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        consultations = patient.consultations.all()
        serializer = ConsultationSerializer(consultations, many=True)
        return Response(serializer.data)        