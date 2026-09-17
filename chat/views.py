# apps/chat/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Conversation, ChatSyncLog, PendingMessageSync
from .serializers import (
    ConversationSerializer, ConversationDetailSerializer,
    ChatSyncLogSerializer, PendingMessageSyncSerializer
)
# from accounts.permissions import IsDoctor, IsPatient


# apps/chat/views.py
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Conversation
from .serializers import ConversationSerializer, ConversationCreateSerializer
from accounts.models import Profile
from accounts.permissions import IsDoctor, IsDoctorOrPatient


class ConversationViewSet(viewsets.ModelViewSet):
    """
    Conversations are driven by `mh_user_id` (+ optional `consultation_id`).
    The doctor is inferred from request.user.
    """

    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsDoctorOrPatient]

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        return ConversationSerializer

    # apps/chat/views.py
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        print(qs)

        if not hasattr(user, 'profile'):
            return qs.none()

        # Staff see everything
        if user.is_staff:
            return qs

        # Patients see only their own
        if hasattr(user.profile, 'patient_profile'):
            return qs.filter(patient_profile=user.profile.patient_profile)

        # Doctors see everything (or restrict to their own — your choice)
        if hasattr(user.profile, 'doctor_profile'):
            return qs
            # If you want "only mine", use:
            # return qs.filter(doctor_profile=user.profile.doctor_profile)

            return qs.none()
    # def get_queryset(self):
    #     qs = super().get_queryset()
    #     user = self.request.user
    #     if not hasattr(user, 'profile'):
    #         return qs.none()

    #     if hasattr(user.profile, 'patient_profile'):
    #         return qs.filter(patient_profile=user.profile.patient_profile)
    #     if hasattr(user.profile, 'doctor_profile'):
    #         return qs.filter(doctor_profile=user.profile.doctor_profile)
    #     if user.is_staff:
    #         return qs
    #     return qs.none()

    def get_permissions(self):
        if self.action == 'create':
            self.permission_classes = [IsDoctor]
        else:
            self.permission_classes = [IsDoctorOrPatient]
        return [p() for p in self.permission_classes]

    # -------------------------------------------------
    # CREATE
    # -------------------------------------------------
    @swagger_auto_schema(
        operation_description=(
            "Create (or reuse) a conversation. "
            "Doctor is taken from request.user. "
            "Patient from mh_user_id. "
            "Optional consultation_id links it to a consultation."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'mh_user_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="Patient's mh_user_id (e.g. MH-2026-1358F4D6)"
                ),
                'consultation_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="Optional consultation to link"
                ),
                'is_active': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="Optional; default: true"
                ),
            },
            required=['mh_user_id'],
        ),
        responses={201: ConversationSerializer()}
    )
    def create(self, request, *args, **kwargs):
        serializer = ConversationCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        conversation = serializer.save()
        return Response(
            ConversationSerializer(conversation).data,
            status=status.HTTP_201_CREATED,
        )

    # -------------------------------------------------
    # FETCH by mh_user_id
    # -------------------------------------------------
    @swagger_auto_schema(
        operation_description="Get conversations by mh_user_id",
        manual_parameters=[
            openapi.Parameter(
                'mh_user_id', openapi.IN_QUERY,
                description="Patient mh_user_id",
                type=openapi.TYPE_STRING, required=True,
            )
        ],
        responses={200: ConversationSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def get_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response(
                {'status': 'error', 'message': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            return Response(
                {'status': 'error', 'message': f"Profile '{mh_user_id}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        patient_profile = getattr(profile, 'patient_profile', None)
        if not patient_profile:
            return Response(
                {'status': 'error', 'message': 'Patient profile not found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        conversations = Conversation.objects.filter(
            patient_profile=patient_profile
        ).order_by('-created_at')

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'patient_profile_id': patient_profile.id,
            'count': conversations.count(),
            'data': ConversationSerializer(conversations, many=True).data,
        })

    # -------------------------------------------------
    # FETCH by consultation_id
    # -------------------------------------------------
    @swagger_auto_schema(
        operation_description="Get the conversation linked to a consultation",
        manual_parameters=[
            openapi.Parameter(
                'consultation_id', openapi.IN_QUERY,
                description="Consultation ID",
                type=openapi.TYPE_INTEGER, required=True,
            )
        ],
        responses={200: ConversationSerializer()}
    )
    @action(detail=False, methods=['get'], url_path='by-consultation')
    def get_by_consultation(self, request):
        consultation_id = request.query_params.get('consultation_id')
        if not consultation_id:
            return Response(
                {'status': 'error', 'message': 'consultation_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conversation = Conversation.objects.filter(
            consultation_id=consultation_id
        ).order_by('-created_at').first()

        if not conversation:
            return Response(
                {'status': 'error', 'message': 'No conversation for this consultation'},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            'status': 'success',
            'data': ConversationSerializer(conversation).data,
        })

    # -------------------------------------------------
    # CLOSE
    # -------------------------------------------------
    @swagger_auto_schema(
        operation_description="Close the conversation",
        responses={200: ConversationSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        conversation = self.get_object()
        conversation.is_active = False
        conversation.ended_at = timezone.now()
        conversation.save()
        return Response(ConversationSerializer(conversation).data)

# ============================================
# ChatSyncLog ViewSet
# ============================================
class ChatSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only view for Chat Sync Logs.
    """
    queryset = ChatSyncLog.objects.all()
    serializer_class = ChatSyncLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['synced_at', 'created_at']
    ordering = ['-synced_at']
    
    def get_queryset(self):
        """Filter sync logs based on user's conversations"""
        user = self.request.user
        queryset = ChatSyncLog.objects.all()
        
        if user.is_staff or user.is_superuser:
            return queryset
        
        try:
            profile = user.profile
            if profile.role == 'patient':
                conversations = Conversation.objects.filter(patient_profile=profile.patient_profile)
            elif profile.role == 'doctor':
                conversations = Conversation.objects.filter(doctor_profile=profile.doctor_profile)
            else:
                return queryset.none()
            return queryset.filter(conversation__in=conversations)
        except:
            return queryset.none()
    
    @swagger_auto_schema(
        operation_description="Get all sync logs",
        responses={200: ChatSyncLogSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get a specific sync log",
        responses={200: ChatSyncLogSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


# ============================================
# PendingMessageSync ViewSet
# ============================================
class PendingMessageSyncViewSet(viewsets.ModelViewSet):
    """
    CRUD operations for Pending Message Sync.
    """
    queryset = PendingMessageSync.objects.all()
    serializer_class = PendingMessageSyncSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering_fields = ['attempt_count', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """Filter pending syncs based on user's conversations"""
        user = self.request.user
        queryset = PendingMessageSync.objects.all()
        
        if user.is_staff or user.is_superuser:
            return queryset
        
        try:
            profile = user.profile
            if profile.role == 'patient':
                conversations = Conversation.objects.filter(patient_profile=profile.patient_profile)
            elif profile.role == 'doctor':
                conversations = Conversation.objects.filter(doctor_profile=profile.doctor_profile)
            else:
                return queryset.none()
            return queryset.filter(conversation__in=conversations)
        except:
            return queryset.none()
    
    @swagger_auto_schema(
        operation_description="Get all pending message syncs",
        responses={200: PendingMessageSyncSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Create a new pending message sync",
        request_body=PendingMessageSyncSerializer,
        responses={201: PendingMessageSyncSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Get a specific pending message sync",
        responses={200: PendingMessageSyncSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Update a pending message sync",
        request_body=PendingMessageSyncSerializer,
        responses={200: PendingMessageSyncSerializer()}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Partially update a pending message sync",
        request_body=PendingMessageSyncSerializer,
        responses={200: PendingMessageSyncSerializer()}
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Delete a pending message sync",
        responses={204: 'No Content'}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry a failed message sync"""
        pending_sync = self.get_object()
        
        if pending_sync.is_processed:
            return Response({
                'status': 'error',
                'message': 'This sync is already processed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        pending_sync.attempt_count += 1
        pending_sync.last_attempt = timezone.now()
        
        if pending_sync.attempt_count >= pending_sync.max_attempts:
            pending_sync.is_processed = True
        
        pending_sync.save()
        
        return Response({
            'status': 'success',
            'message': 'Retry initiated',
            'data': self.get_serializer(pending_sync).data
        })
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Get all pending message syncs"""
        queryset = self.get_queryset().filter(is_processed=False)
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'count': queryset.count(),
            'data': serializer.data
        })