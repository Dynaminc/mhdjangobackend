# apps/files/urls.py
from django.urls import path
from .views import FileUploadView, FileServeView

urlpatterns = [
    path('', FileUploadView.as_view()),                 # POST /api/v1/files/
    path('<uuid:file_id>/', FileServeView.as_view()),   # GET  /api/v1/files/{id}/
]