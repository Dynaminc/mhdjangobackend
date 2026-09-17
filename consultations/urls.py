# apps/consultations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConsultationViewSet,
    ExaminationViewSet,
    PastMedicalHistoryViewSet,
    MedicalRecordViewSet
)

router = DefaultRouter()
router.register(r'consultations', ConsultationViewSet, basename='consultation')
router.register(r'examinations', ExaminationViewSet, basename='examination')
router.register(r'medical-histories', PastMedicalHistoryViewSet, basename='medical-history')
router.register(r'medical-records', MedicalRecordViewSet, basename='medical-record')

urlpatterns = [
    path('', include(router.urls)),
]
