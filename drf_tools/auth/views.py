from django.contrib.auth import login, logout
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from rest_framework.viewsets import GenericViewSet

from drf_tools.auth.authentications import QuietBasicAuthentication
from drf_tools.auth.filters import PermissionAwareFilterBackend
from drf_tools.auth.permissions import BusinessPermission
from drf_tools.auth.serializers import UserSerializer


class AuthView(GenericViewSet):
    authentication_classes = (QuietBasicAuthentication, SessionAuthentication)
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        login(request, request.user)
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        logout(request)
        return Response({}, status.HTTP_204_NO_CONTENT)


class BusinessPermissionFilteredViewMixin(object):
    queryset = None
    permission_classes = (BusinessPermission,)
    filter_backends = (PermissionAwareFilterBackend,)

    def filter_queryset_by_permission(self, qs, user, permission_model_id):
        if self.queryset is None:
            raise ValueError("queryset must be set")

        return self._get_permission_filtering().filter(qs, user, permission_model_id)

    def _get_permission_filtering(self):
        raise NotImplementedError()
