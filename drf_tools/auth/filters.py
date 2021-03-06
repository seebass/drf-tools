from django_filters.rest_framework import DjangoFilterBackend

from drf_tools.auth.permissions import permission_service


def _is_detail_method(view):
    return view.kwargs.get('pk')


class PermissionAwareFilterBackend(DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        qs = super().filter_queryset(request, queryset, view)
        if _is_detail_method(view):
            return qs
        filter_param = permission_service.get_permission_model_filter_param(view.queryset.model)
        return view.filter_queryset_by_permission(
            qs, request.user, request.query_params.get(filter_param))
