"""
POST /api/verification  (multipart: id_document, selfie)

Stores both files to private media (local in dev, S3 in prod via
DEFAULT_FILE_STORAGE), then flips the user's verification_status to 'pending'.
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


class VerificationView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes_override = None  # let DRF handle multipart via its default parsers

    def post(self, request):
        id_doc = request.FILES.get('id_document')
        selfie = request.FILES.get('selfie')

        if not id_doc or not selfie:
            return Response(
                {'detail': 'Both id_document and selfie files are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        prefix = f'verification/{user.pk}'

        # Store under a private path; the storage backend (local or S3) controls access.
        id_path = default_storage.save(f'{prefix}/id_{id_doc.name}', ContentFile(id_doc.read()))
        selfie_path = default_storage.save(f'{prefix}/selfie_{selfie.name}', ContentFile(selfie.read()))

        user.verification_status = 'pending'
        user.save(update_fields=['verification_status'])

        return Response({'status': 'pending', 'id_path': id_path, 'selfie_path': selfie_path})
