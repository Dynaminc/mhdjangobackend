# apps/specialists/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets import (
    SpecialistViewSet,
    SpecialistReferralViewSet,
    SpecialistReviewViewSet,
    SpecialistTagViewSet,
)

router = DefaultRouter()
router.register(r'specialists', SpecialistViewSet, basename='specialist')
router.register(r'referrals', SpecialistReferralViewSet, basename='referral')
router.register(r'reviews', SpecialistReviewViewSet, basename='review')
router.register(r'tags', SpecialistTagViewSet, basename='tag')

urlpatterns = [path('', include(router.urls))]