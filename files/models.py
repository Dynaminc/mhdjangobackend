# apps/files/models.py
import uuid
from django.db import models
from django.conf import settings


class SecureFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='files',
    )
    filename = models.CharField(max_length=255)
    mime = models.CharField(max_length=100, blank=True)
    path = models.CharField(max_length=500)          # relative path on disk
    size = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.id})"