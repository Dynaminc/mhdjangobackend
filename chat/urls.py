# apps/chat/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet, ChatSyncLogViewSet, 
    PendingMessageSyncViewSet
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'sync-logs', ChatSyncLogViewSet, basename='sync-log')
router.register(r'pending-sync', PendingMessageSyncViewSet, basename='pending-sync')

urlpatterns = [
    path('', include(router.urls)),
]