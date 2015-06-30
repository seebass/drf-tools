from collections import OrderedDict

from django.core.urlresolvers import NoReverseMatch
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView

from drf_nested_routing.routers import NestedRouterMixin


class NestedRouterWithExtendedRootView(NestedRouterMixin, DefaultRouter):
    """
    Router that handles nested routes and additionally adds given api_view_urls to the ApiRootView (the api entrypoint)
    """
    def __init__(self, api_view_urls):
        self.__api_view_urls = api_view_urls
        super(NestedRouterWithExtendedRootView, self).__init__()

    def get_api_root_view(self):
        api_root_routes = {}
        list_name = self.routes[0].name
        for prefix, viewset, basename in self.registry:
            api_root_routes[prefix] = list_name.format(basename=basename)

        api_view_urls = self.__api_view_urls

        class ApiRootView(APIView):

            permission_classes = (AllowAny,)

            def get(self, request, *args, **kwargs):
                links = OrderedDict()
                links['viewsets'] = OrderedDict()
                for key, url_name in api_root_routes.items():
                    try:
                        links['viewsets'][key] = reverse(url_name, request=request, format=kwargs.get('format', None))
                    except NoReverseMatch:
                        continue

                links['views'] = OrderedDict()
                for api_view_url in api_view_urls:
                    url_name = api_view_url.name
                    try:
                        if '<pk>' in api_view_url._regex:
                            links['views'][url_name] = reverse(url_name, request=request,
                                                              format=kwargs.get('format', None), args=(0,))
                        else:
                            links['views'][url_name] = reverse(url_name, request=request,
                                                              format=kwargs.get('format', None))
                    except NoReverseMatch as e:
                        continue

                return Response({"_links": links})

        return ApiRootView().as_view()
