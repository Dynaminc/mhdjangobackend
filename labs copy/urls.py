# apps/labs/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LabTestCatalogViewSet,
    LabTestOrderViewSet,
    LabPanelViewSet,
    LabTestProfileViewSet,
    LabOrderTemplateViewSet
)

# router.register(r'results', LabTestResultViewSet, basename='lab-result')
router = DefaultRouter()
router.register(r'test-catalog', LabTestCatalogViewSet, basename='lab-test-catalog')
router.register(r'orders', LabTestOrderViewSet, basename='lab-order')

router.register(r'panels', LabPanelViewSet, basename='lab-panel')
router.register(r'profiles', LabTestProfileViewSet, basename='lab-profile')
router.register(r'templates', LabOrderTemplateViewSet, basename='lab-template')

urlpatterns = [
    path('', include(router.urls)),
]