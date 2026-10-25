# # apps/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from . import views

router = DefaultRouter()
from django.urls import path

from .views import register_device,test_push

urlpatterns = [
    path(
        "register/",
        register_device,
        name="register-notification-device",
    ),
    path("devices/test-push/", test_push, name="test-push"),
]
# urlpatterns = [
#     path('', include(router.urls)),
# ]
