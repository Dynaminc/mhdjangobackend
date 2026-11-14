# # apps/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from . import views

router = DefaultRouter()
from django.urls import path

from .views import register_device,test_push
from .views import NotificationViewSet, NotificationPreferenceViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path(
        "register/",
        register_device,
        name="register-notification-device",
    ),
    path("devices/test-push/", test_push, name="test-push"),
    
    path(
        'notifications/preferences/',
        NotificationPreferenceViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='notification-preferences',
    ),
]
# urlpatterns = [
#     path('', include(router.urls)),
# ]
