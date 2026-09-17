# apps/appointments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClinicViewSet,
    AppointmentViewSet,
    QueueEntryViewSet,
    QueueViewSet,
    DoctorAvailabilityViewSet
)

router = DefaultRouter()
router.register(r'clinics', ClinicViewSet, basename='clinic')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
# router.register(r'queue', QueueEntryViewSet, basename='queue-entry')
# router.register(r'queue', QueueEntryViewSet, basename='queue-entry')

router.register(r'queue', QueueViewSet, basename='queue')
router.register(r'availability', DoctorAvailabilityViewSet, basename='doctor-availability')

urlpatterns = [
    path('', include(router.urls)),
]