from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny

from schools.models import Grade
from schools.serializers import GradeSerializer


class GradeListView(ListAPIView):
    queryset = Grade.objects.all().order_by("level")
    serializer_class = GradeSerializer
    permission_classes = [AllowAny]
