from copy import copy

from urllib.parse import urlsplit

from django.core import urlresolvers
from django.conf import settings
from django_tooling.moduleloading import load_module
from drf_hal_json import LINKS_FIELD_NAME
import drf_nested_routing
from drf_tools.utils import is_detail_uri
from rest_framework.exceptions import PermissionDenied

from rest_framework.permissions import BasePermission, SAFE_METHODS

from rest_framework.request import Request

from rest_framework.settings import api_settings
from drf_tools.auth import PERMISSION_SERVICE

from drf_tools.auth.models import Operation

permission_service = load_module(PERMISSION_SERVICE)()


def check_base_permissions(request, user):
    if permission_service.is_super_user(user) or (permission_service.is_super_reader(user) and request.method in SAFE_METHODS):
        return True
    if request.method == "OPTIONS":
        return True
    if is_detail_uri(request.path) or request.method in ("GET", 'HEAD'):
        # detail requests are handled in has_object_permission
        # GET/HEAD on list endpoints are filtered in PermissionAwareFilterBackend
        return True


class BusinessPermission(BasePermission):
    """
    Permission that handles business dependend permissions.
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated():
            return False

        if check_base_permissions(request, user):
            return True

        if not permission_service.is_valid_model(view.queryset.model):
            return False

        if request.method == 'POST':
            permission_model_ids = permission_service.get_permission_model_ids_from_request(request, view)
            if not self._check_links(request):
                return False
            for permission_model_id in permission_model_ids:
                if permission_service.has_permission(user, permission_model_id, view.queryset.model, Operation.CREATE):
                    return True

        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if permission_service.is_super_user(user) or (
            permission_service.is_super_reader(user) and request.method in SAFE_METHODS):
            return True
        if request.method in ('PUT', 'PATCH') and not self._check_links(request):
            return False
        operation = self.__get_operation(request.method)
        return permission_service.has_object_permission(user, obj, operation)

    def _check_links(self, request):
        if LINKS_FIELD_NAME in request.data:
            urlconf = settings.ROOT_URLCONF
            urlresolvers.set_urlconf(urlconf)
            resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
            for key, urls in request.data[LINKS_FIELD_NAME].items():
                if key == api_settings.URL_FIELD_NAME:
                    continue  # we don't check the object itself
                if not type(urls) is list:
                    urls = [urls]
                for url in urls:
                    if not self._can_read_url(request, url, resolver, key):
                        return False
        return True

    def _can_read_url(self, request, url, resolver, key):
        if url is None:
            return True
        sub_request = self.__make_sub_request(request, url, resolver)
        view, Model, obj = self.__get_view_model_object_for_request(sub_request)
        if not obj:
            raise Model.DoesNotExist(url)
        try:
            view.check_permissions(sub_request)
            view.check_object_permissions(sub_request, obj)
            return True
        except PermissionDenied:
            return False

    @staticmethod
    def __make_sub_request(request, url, resolver):
        wsgi_request = copy(request._request)
        wsgi_request.method = 'GET'
        wsgi_request.path = wsgi_request.path_info = urlsplit(url).path
        wsgi_request.resolver_match = resolver.resolve(wsgi_request.path_info)
        sub_request = Request(wsgi_request)
        sub_request.user = request.user
        sub_request.authenticators = request.authenticators
        return sub_request

    @staticmethod
    def __get_view_model_object_for_request(request):
        callback, callback_args, callback_kwargs = request.resolver_match
        ModelCls = callback.cls.queryset.model
        lookups = {}
        for k, v in callback_kwargs.items():
            if k.startswith(drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX):
                k = k[len(drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX):]
            lookups[k] = v
        queryset = ModelCls.objects.filter(**lookups)
        return callback.cls(), ModelCls, queryset.first()

    @staticmethod
    def __get_operation(method):
        if method == "PUT" or method == "PATCH":
            return Operation.UPDATE
        elif method == "POST":
            return Operation.CREATE
        elif method == "DELETE":
            return Operation.DELETE
        return Operation.READ


class IsSuperUserPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            return False
        return permission_service.is_super_user(request.user)


class IsSuperUserOrAuthenticatedReadOnlyPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            return False
        if request.method in SAFE_METHODS:
            return True
        return permission_service.is_super_user(request.user)


class IsSuperUserOrReadOnlyPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return permission_service.is_super_user(request.user)


class IsSuperUserOrBusinessAdminReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated():
            return False

        if request.method in SAFE_METHODS and permission_service.is_business_admin(request.user):
            return True

        return permission_service.is_super_user(request.user)
