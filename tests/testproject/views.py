from drf_nested_routing.views import NestedViewSetMixin

from drf_tools.views import ModelViewSet
from .models import TestResource, RelatedResource2, RelatedResource1


class TestResourceViewSet(ModelViewSet):
    queryset = TestResource.objects.all()


class RelatedResource1ViewSet(NestedViewSetMixin, ModelViewSet):
    queryset = RelatedResource1.objects.all()


class RelatedResource2ViewSet(NestedViewSetMixin, ModelViewSet):
    queryset = RelatedResource2.objects.all()
