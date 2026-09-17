# apps/prescriptions/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MedicationCatalogViewSet,
    PrescriptionViewSet,
    RefillRequestViewSet,
    MedicationInteractionViewSet,
    MedicationAdherenceViewSet
)

router = DefaultRouter()
router.register(r'medications', MedicationCatalogViewSet, basename='medication-catalog')
router.register(r'prescriptions', PrescriptionViewSet, basename='prescription')
router.register(r'refill-requests', RefillRequestViewSet, basename='refill-request')
router.register(r'interactions', MedicationInteractionViewSet, basename='medication-interaction')
router.register(r'adherence', MedicationAdherenceViewSet, basename='medication-adherence')

urlpatterns = [
    path('', include(router.urls)),
]