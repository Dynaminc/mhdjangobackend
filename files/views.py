# apps/files/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from .models import SecureFile
from .storage import save_file, read_file


class FileUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        f = request.FILES.get('file')
        if not f:
            return Response({'error': 'file required'}, status=400)

        rel_path, enc_size = save_file(f.read())

        sf = SecureFile.objects.create(
            owner=request.user,
            filename=f.name,
            mime=f.content_type or '',
            path=rel_path,
            size=f.size,
        )

        return Response({
            'id': str(sf.id),
            'url': f'/api/v1/files/{sf.id}/',
            'filename': sf.filename,
            'size': sf.size,
            'encrypted_size': enc_size,
        }, status=status.HTTP_201_CREATED)


class FileServeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        sf = get_object_or_404(SecureFile, id=file_id)

        # Access: owner, any doctor, any admin
        profile = getattr(request.user, 'profile', None)
        is_owner = sf.owner_id == request.user.id
        is_doctor = bool(profile and profile.role == 'doctor')
        is_admin = request.user.is_staff

        if not (is_owner or is_doctor or is_admin):
            return Response({'error': 'forbidden'}, status=403)

        try:
            raw = read_file(sf.path)
        except FileNotFoundError:
            return Response({'error': 'file missing on disk'}, status=404)

        response = HttpResponse(raw, content_type=sf.mime or 'application/octet-stream')
        response['Content-Disposition'] = f'inline; filename="{sf.filename}"'
        response['Content-Length'] = len(raw)
        return response