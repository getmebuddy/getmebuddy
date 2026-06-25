from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from .models import BlockedUser, Report
from .serializers import ReportSerializer

User = get_user_model()


class BlockedUserView(APIView):
    """POST /api/users/{id}/block  —  DELETE /api/users/{id}/block"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            return Response({'detail': 'Cannot block yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        BlockedUser.objects.get_or_create(blocker=request.user, blocked=target)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        BlockedUser.objects.filter(blocker=request.user, blocked=target).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BlockedListView(APIView):
    """GET /api/users/me/blocked  —  returns list of blocked user IDs"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ids = list(
            BlockedUser.objects.filter(blocker=request.user).values_list('blocked_id', flat=True)
        )
        return Response(ids)


class ReportView(APIView):
    """POST /api/reports"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        data = request.data.copy()
        target_user_id = data.pop('target_user_id', None)

        report = Report(
            reporter=request.user,
            target_type=data.get('target_type', 'user'),
            target_id=data.get('target_id', ''),
            reason=data.get('reason', ''),
            details=data.get('details', ''),
            status='received',
        )
        if target_user_id:
            target = User.objects.filter(pk=target_user_id).first()
            report.target_user = target

        report.save()
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
