# apps/labs/viewsets.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import LabTestOrder
from .serializers import LabTestOrderSerializer, LabTestOrderCreateSerializer
from accounts.permissions import IsDoctorOrPatient, IsAdmin
from accounts.models import Profile, PatientProfile
from consultations.models import Consultation
from django.db import transaction

class LabTestOrderViewSet(viewsets.ModelViewSet):
    queryset = LabTestOrder.objects.all()
    permission_classes = [IsDoctorOrPatient | IsAdmin]

    def get_serializer_class(self):
        if self.action == 'create':
            return LabTestOrderCreateSerializer
        return LabTestOrderSerializer

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
        serializer = LabTestOrderCreateSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(
            LabTestOrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Fetch by patient ─────────────────────────────────
    @swagger_auto_schema(
        operation_description="Get lab orders by mh_user_id",
        manual_parameters=[
            openapi.Parameter('mh_user_id', openapi.IN_QUERY,
                              type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: LabTestOrderSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='by-mh-user-id')
    def get_by_mh_user_id(self, request):
        mh_user_id = request.query_params.get('mh_user_id')
        if not mh_user_id:
            return Response(
                {'error': 'mh_user_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = LabTestOrder.objects.filter(
            patient_profile__profile__mh_user_id=mh_user_id
        ).order_by('-created_at')

        return Response({
            'status': 'success',
            'mh_user_id': mh_user_id,
            'count': qs.count(),
            'data': LabTestOrderSerializer(qs, many=True).data,
        })

    # ── Fetch by consultation ────────────────────────────
    @swagger_auto_schema(
        operation_description="Get lab orders by consultation_id",
        manual_parameters=[
            openapi.Parameter('consultation_id', openapi.IN_QUERY,
                              type=openapi.TYPE_INTEGER, required=True),
        ],
        responses={200: LabTestOrderSerializer(many=True)},
    )
    @action(detail=False, methods=['get'], url_path='by-consultation')
    def get_by_consultation(self, request):
        consultation_id = request.query_params.get('consultation_id')
        if not consultation_id:
            return Response(
                {'error': 'consultation_id is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = LabTestOrder.objects.filter(
            consultation_id=consultation_id
        ).order_by('created_at')

        return Response({
            'status': 'success',
            'consultation_id': int(consultation_id),
            'count': qs.count(),
            'data': LabTestOrderSerializer(qs, many=True).data,
        })

    # ── Attach result / files later ──────────────────────
    @action(detail=True, methods=['post'], url_path='set-result')
    def set_result(self, request, pk=None):
        lab = self.get_object()

        profile = getattr(request.user, 'profile', None)
        if profile is None:
            return Response(
                {'error': 'Profile required'},
                status=status.HTTP_403_FORBIDDEN,
            )

        is_staff = request.user.is_staff
        is_ordering_doctor = (
            profile.role == 'doctor'
            and lab.doctor_profile_id == getattr(profile.doctor_profile, 'id', None)
        )
        is_owner_patient = (
            profile.role == 'patient'
            and lab.patient_profile_id == getattr(profile.patient_profile, 'id', None)
        )

        if not (is_staff or is_ordering_doctor or is_owner_patient):
            return Response(
                {'error': 'You cannot modify results for this lab order'},
                status=status.HTTP_403_FORBIDDEN,
            )

        updated = []

        # ── result_value — patient or doctor ─────────────
        if 'result_value' in request.data:
            lab.result_value = (request.data.get('result_value') or '').strip()
            updated.append('result_value')

        # ── attachment_urls — patient or doctor ──────────
        if 'attachment_urls' in request.data:
            urls = request.data.get('attachment_urls') or []
            if not isinstance(urls, list):
                return Response(
                    {'error': 'attachment_urls must be a list'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            lab.attachment_urls = list(dict.fromkeys(urls))
            updated.append('attachment_urls')

        # ── doctor_comment — ONLY the ordering doctor or staff ──
        if 'doctor_comment' in request.data:
            if not (is_staff or is_ordering_doctor):
                return Response(
                    {'error': 'Only the ordering doctor can add a comment'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            lab.doctor_comment = (request.data.get('doctor_comment') or '').strip()
            updated.append('doctor_comment')

        if updated:
            lab.save(update_fields=updated)

        return Response(LabTestOrderSerializer(lab).data)

    @swagger_auto_schema(
        operation_description="Replace the entire lab order list for a consultation",
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
                            'test_name': openapi.Schema(type=openapi.TYPE_STRING),
                            'instructions': openapi.Schema(type=openapi.TYPE_STRING),
                            'clinical_indication': openapi.Schema(type=openapi.TYPE_STRING),
                        },
                    ),
                ),
            },
            required=['mh_user_id', 'items'],
        ),
        responses={200: LabTestOrderSerializer(many=True)},
    )
    @action(detail=False, methods=['post'], url_path='replace-list')
    def replace_list(self, request):
        from rest_framework.exceptions import ValidationError, PermissionDenied

        mh_user_id = request.data.get('mh_user_id')
        consultation_id = request.data.get('consultation_id')
        items = request.data.get('items', [])

        if not mh_user_id:
            raise ValidationError({'mh_user_id': 'required'})
        if not isinstance(items, list):
            raise ValidationError({'items': 'must be a list'})

        # Resolve patient
        try:
            profile = Profile.objects.get(mh_user_id=mh_user_id)
        except Profile.DoesNotExist:
            raise ValidationError({'mh_user_id': 'not found'})
        patient_profile = getattr(profile, 'patient_profile', None)
        if patient_profile is None:
            patient_profile = PatientProfile.objects.create(profile=profile)

        # Resolve doctor
        doctor = getattr(request.user.profile, 'doctor_profile', None)
        if not doctor:
            raise PermissionDenied('Only doctors can modify lab orders.')

        # Resolve consultation
        consultation = None
        if consultation_id:
            try:
                consultation = Consultation.objects.get(id=consultation_id)
            except Consultation.DoesNotExist:
                raise ValidationError({'consultation_id': 'not found'})
            if consultation.patient_profile_id != patient_profile.id:
                raise ValidationError(
                    {'consultation_id': 'does not belong to this patient'}
                )

        with transaction.atomic():
            # Delete existing orders for this (patient, doctor, consultation)
            qs = LabTestOrder.objects.filter(
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
                LabTestOrder.objects.create(
                    consultation=consultation,
                    patient_profile=patient_profile,
                    doctor_profile=doctor,
                    test_name=item.get('test_name', '').strip(),
                    instructions=item.get('instructions', ''),
                    clinical_indication=item.get('clinical_indication', ''),
                )
                for item in items
                if item.get('test_name')
            ]

        return Response({
            'status': 'success',
            'count': len(created),
            'data': LabTestOrderSerializer(created, many=True).data,
        })    