from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.db.models import Q

from .models import Activity
from .serializers import ActivitySerializer, ActivityCreateSerializer


class ActivityListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/activities            — list open activities, optional filters
    GET  /api/activities?category=  — filter by category
    GET  /api/activities?bbox=minLng,minLat,maxLng,maxLat  — viewport filter
    POST /api/activities            — create a new activity (host = request.user)
    """
    permission_classes = [permissions.IsAuthenticated]
    # Client expects a plain JSON array, not a paginated envelope.
    pagination_class = None

    def get_serializer_class(self):
        return ActivityCreateSerializer if self.request.method == 'POST' else ActivitySerializer

    def get_queryset(self):
        qs = Activity.objects.select_related('host').filter(status=Activity.STATUS_OPEN)

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        bbox = self.request.query_params.get('bbox')
        if bbox:
            try:
                min_lng, min_lat, max_lng, max_lat = (float(v) for v in bbox.split(','))
                qs = qs.filter(
                    latitude__gte=min_lat,
                    latitude__lte=max_lat,
                    longitude__gte=min_lng,
                    longitude__lte=max_lng,
                )
            except (ValueError, TypeError):
                pass  # malformed bbox — return unfiltered

        limit = self.request.query_params.get('limit')
        if limit:
            try:
                qs = qs[:int(limit)]
            except (ValueError, TypeError):
                pass

        return qs

    def create(self, request, *args, **kwargs):
        serializer = ActivityCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        activity = serializer.save()
        return Response(ActivitySerializer(activity).data, status=status.HTTP_201_CREATED)


class ActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/activities/{id}
    PATCH  /api/activities/{id}   — host only
    DELETE /api/activities/{id}   — host only
    """
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Activity.objects.select_related('host').all()

    def update(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.host != request.user:
            return Response({'detail': 'Only the host can edit this activity.'}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        activity = self.get_object()
        if activity.host != request.user:
            return Response({'detail': 'Only the host can delete this activity.'}, status=403)
        return super().destroy(request, *args, **kwargs)
