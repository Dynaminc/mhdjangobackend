# apps/specialists/viewsets.py
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .throttles import (
    ReferralAnonThrottle,
    ReferralEmailThrottle,
    ReferralUserThrottle,
)

from .models import (
    Specialist,
    SpecialistReferral,
    SpecialistReview,
    SpecialistTag,
)
from .serializers import (
    SpecialistListSerializer,
    SpecialistDetailSerializer,
    SpecialistWriteSerializer,
    SpecialistReferralSerializer,
    SpecialistReferralCreateSerializer,
    SpecialistReferralStatusUpdateSerializer,
    SpecialistReviewSerializer,
    SpecialistTagSerializer,
)
from accounts.permissions import IsAdminUser


# =====================================================
# SPECIALIST VIEWSET (public directory + admin CRUD)
# =====================================================
class SpecialistViewSet(viewsets.ModelViewSet):
    """
    Public directory + admin CRUD.

    - list:     anyone (filter by specialty, country, status, etc.)
    - retrieve: anyone
    - create/update/delete: admin only
    """
    queryset = Specialist.objects.filter(is_active=True)
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return SpecialistWriteSerializer
        if self.action == 'retrieve':
            return SpecialistDetailSerializer
        return SpecialistListSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = Specialist.objects.all()
        # public: only active
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            qs = qs.filter(is_active=True)

        # filters
        specialty = self.request.query_params.get('specialty')
        country = self.request.query_params.get('country')
        status_filter = self.request.query_params.get('status')
        is_remote = self.request.query_params.get('is_remote')
        is_featured = self.request.query_params.get('is_featured')
        search = self.request.query_params.get('search')

        if specialty:
            qs = qs.filter(specialty=specialty)
        if country:
            qs = qs.filter(country__iexact=country)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if is_remote in ('true', '1'):
            qs = qs.filter(is_remote=True)
        if is_featured in ('true', '1'):
            qs = qs.filter(is_featured=True)
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(headline__icontains=search) |
                Q(short_bio__icontains=search)
            )
        return qs

    @swagger_auto_schema(
        operation_description="List specialists (public directory)",
        manual_parameters=[
            openapi.Parameter('specialty', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('country', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('is_remote', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('is_featured', openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
        responses={200: SpecialistListSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Get a specialist profile by slug",
        responses={200: SpecialistDetailSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_description="Get featured specialists",
        responses={200: SpecialistListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='featured')
    def featured(self, request):
        qs = Specialist.objects.filter(is_active=True, is_featured=True)
        return Response({
            'status': 'success',
            'count': qs.count(),
            'data': SpecialistListSerializer(qs, many=True).data,
        })

    @swagger_auto_schema(
        operation_description="Get available-now specialists",
        responses={200: SpecialistListSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='available-now')
    def available_now(self, request):
        qs = Specialist.objects.filter(is_active=True, status='available')
        return Response({
            'status': 'success',
            'count': qs.count(),
            'data': SpecialistListSerializer(qs, many=True).data,
        })

    @swagger_auto_schema(
        operation_description="List distinct specialties (for filter dropdown)",
        responses={200: openapi.Response('Specialties')}
    )
    @action(detail=False, methods=['get'], url_path='specialties')
    def specialties(self, request):
        from .models import Specialty
        return Response({
            'status': 'success',
            'data': [
                {'value': v, 'label': l}
                for v, l in Specialty.choices
            ],
        })


# =====================================================
# REFERRAL VIEWSET
# =====================================================
class SpecialistReferralViewSet(viewsets.ModelViewSet):
    """
    Patient submits a referral.
    Admin reviews and changes status.
    """
    queryset = SpecialistReferral.objects.all()
    permission_classes = [permissions.AllowAny]


    # def get_throttles(self):
    #     """
    #     Different limits per action:
    #       - create: anon + email + user throttles
    #       - others: default (admin only anyway)
    #     """
    #     if self.action == 'create':
    #         return [
    #             ReferralAnonThrottle(),
    #             ReferralEmailThrottle(),
    #             ReferralUserThrottle(),
    #         ]
    #     return super().get_throttles()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SpecialistReferralCreateSerializer
        if self.action == 'update_status':
            return SpecialistReferralStatusUpdateSerializer
        return SpecialistReferralSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'update_status', 'destroy']:
            return [IsAdminUser()]
        # create is open to public
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = SpecialistReferralCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral = serializer.save()
        return Response(
            {
                'status': 'success',
                'message': 'Referral submitted. We will review and contact you shortly.',
                'data': SpecialistReferralSerializer(referral).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @swagger_auto_schema(
        operation_description="List all referrals (admin only)",
        manual_parameters=[
            openapi.Parameter('status', openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter('search', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
        responses={200: SpecialistReferralSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()

        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')

        if status_filter:
            qs = qs.filter(status=status_filter)
        if search:
            qs = qs.filter(
                Q(reference_id__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )

        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                SpecialistReferralSerializer(page, many=True).data
            )
        return Response(SpecialistReferralSerializer(qs, many=True).data)



    @swagger_auto_schema(
        operation_description="Look up a referral by reference ID (public, tells the frontend what to do next)",
        manual_parameters=[
            openapi.Parameter('ref_id', openapi.IN_QUERY,
                              type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: openapi.Response('Referral lookup')}
    )
    @action(
        detail=False,
        methods=['get'],
        url_path='by-ref',
        permission_classes=[permissions.AllowAny],
        # ✅ Optional auth — allows a token if present, doesn't 401 without one
        # authentication_classes=[JWTAuthentication, SessionAuthentication],
    )
    def by_ref(self, request):
        ref_id = request.query_params.get('ref_id')

        if not ref_id:
            return Response(
                {'status': 'error', 'message': 'ref_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            referral = SpecialistReferral.objects.get(reference_id=ref_id)
        except SpecialistReferral.DoesNotExist:
            return Response({
                'status': 'success',
                'data': {
                    'reference_id': ref_id,
                    'exists': False,
                    'next_action': 'not_found',
                },
            })

        # Who is making this request?
        print(request.user)
        user = request.user if request.user.is_authenticated else None
        is_linked = referral.linked_user_id is not None
        is_same_user = bool(user and is_linked and referral.linked_user_id == user.id)

        # Decide next_action
        if is_same_user:
            next_action = 'schedule'
        elif user and is_linked and user.is_authenticated:
            next_action = 'view'
        elif user and not is_linked:
            # Logged-in user with an unlinked referral — link on the fly?
            next_action = 'schedule'      # or 'link' — your call
        elif is_linked:
            next_action = 'sign_in'
        else:
            next_action = 'sign_up'

        # Build the summary
        data = {
            'reference_id': referral.reference_id,
            'exists': True,
            'first_name': referral.first_name,
            'status': referral.status,
            'status_display': referral.get_status_display(),
            'submitted_at': referral.submitted_at,

            # 👇 the fields the frontend keys off
            'is_linked': is_linked,
            'is_authenticated': user is not None,
            'is_same_user': is_same_user,
            'next_action': next_action,
        }

        # Include scheduling info only when appropriate
        if next_action == 'schedule':
            data.update({
                'appointment_date': referral.appointment_date,
                'appointment_time': referral.appointment_time,
                'meeting_link': referral.meeting_link,
                'assigned_specialist': (
                    referral.assigned_specialist.full_name
                    if referral.assigned_specialist else None
                ),
            })

        return Response({
            'status': 'success',
            'data': data,
        })        

    @swagger_auto_schema(
        operation_description="Change a referral's status (admin only)",
        request_body=SpecialistReferralStatusUpdateSerializer,
        responses={200: SpecialistReferralSerializer()}
    )
    @action(detail=True, methods=['post'], url_path='update-status',
            permission_classes=[IsAdminUser])
    def update_status(self, request, pk=None):
        referral = self.get_object()
        serializer = SpecialistReferralStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_status = data['status']

        # Assign specialist if provided
        if data.get('assigned_specialist_id'):
            try:
                referral.assigned_specialist = Specialist.objects.get(
                    id=data['assigned_specialist_id']
                )
            except Specialist.DoesNotExist:
                return Response(
                    {'error': 'Specialist not found'},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # Apply status transitions
        # apps/specialists/viewsets.py — inside update_status()

        if new_status == 'approved':
            referral.approved_at = timezone.now()
        elif new_status == 'rejected':
            referral.rejected_at = timezone.now()
            referral.rejection_reason = data.get('rejection_reason', '')
        elif new_status == 'scheduled':
            referral.meeting_link = data.get('meeting_link', '') or referral.meeting_link
            referral.appointment_date = data.get('appointment_date') or referral.appointment_date
            referral.appointment_time = data.get('appointment_time') or referral.appointment_time
            
    
        referral.status = new_status
        if data.get('review_notes'):
            referral.review_notes = data['review_notes']
        referral.reviewed_by = request.user
        referral.save()

        return Response({
            'status': 'success',
            'message': f'Referral moved to {new_status}',
            'data': SpecialistReferralSerializer(referral).data,
        })

    @swagger_auto_schema(
        operation_description="Look up a referral by reference_id (patient)",
        manual_parameters=[
            openapi.Parameter('reference_id', openapi.IN_QUERY,
                              type=openapi.TYPE_STRING, required=True)
        ],
        responses={200: SpecialistReferralSerializer()}
    )
    @action(detail=False, methods=['get'], url_path='lookup',
            permission_classes=[permissions.AllowAny])
    def lookup(self, request):
        ref = request.query_params.get('reference_id')
        if not ref:
            return Response(
                {'error': 'reference_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            referral = SpecialistReferral.objects.get(reference_id=ref)
        except SpecialistReferral.DoesNotExist:
            return Response(
                {'error': 'Referral not found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({
            'status': 'success',
            'data': SpecialistReferralSerializer(referral).data,
        })


# =====================================================
# REVIEW VIEWSET
# =====================================================
class SpecialistReviewViewSet(viewsets.ModelViewSet):
    queryset = SpecialistReview.objects.filter(is_published=True)
    serializer_class = SpecialistReviewSerializer
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        qs = SpecialistReview.objects.filter(is_published=True)
        specialist_slug = self.request.query_params.get('specialist')
        if specialist_slug:
            qs = qs.filter(specialist__slug=specialist_slug)
        return qs

    def perform_create(self, serializer):
        serializer.save(reviewer=self.request.user)


# =====================================================
# TAG VIEWSET (read-only list for filters)
# =====================================================
class SpecialistTagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = SpecialistTag.objects.all()
    serializer_class = SpecialistTagSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_description="List distinct tag names for the filter UI",
    )
    @action(detail=False, methods=['get'], url_path='distinct')
    def distinct(self, request):
        names = SpecialistTag.objects.values_list('name', flat=True).distinct()
        return Response({'status': 'success', 'data': list(names)}) 