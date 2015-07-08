from django.conf.urls import patterns, url, include

from django.contrib import admin

from drf_tools.routers import NestedRouterWithExtendedRootView
from .views import TestResourceViewSet, RelatedResource1ViewSet, RelatedResource2ViewSet

admin.autodiscover()

router = NestedRouterWithExtendedRootView(list())
test_resource_route = router.register(r'test-resources', TestResourceViewSet)
test_resource_route.register(r'related-1', RelatedResource1ViewSet, ['resource'])
test_resource_route.register(r'related-2', RelatedResource2ViewSet, ['resource'])

urlpatterns = patterns(
    '',
    url(r'', include(router.urls)),
)
