from abc import ABCMeta, abstractmethod

from drf_hal_json import LINKS_FIELD_NAME, is_hal_content_type
import drf_nested_routing

from drf_tools.utils import get_id_from_detail_uri


class BasePermissionService(object, metaclass=ABCMeta):
    @abstractmethod
    def is_business_admin(self, user, permission_model_id=None, **kwargs):
        pass

    @abstractmethod
    def get_permission_model_attr(self, model):
        pass

    @abstractmethod
    def get_permission_model_filter_param(self, model):
        pass

    @abstractmethod
    def get_permission_model_ids_from_object(self, obj):
        pass

    @abstractmethod
    def has_permission(self, user, permission_model_id, model, operation, **kwargs):
        pass

    @abstractmethod
    def has_object_permission(self, user, obj, operation):
        pass

    @staticmethod
    def is_super_user(user):
        return user.is_superuser

    @staticmethod
    def is_super_reader(user):
        return user.is_staff

    def is_valid_model(self, model):
        return self.get_permission_model_attr(model) is not None

    def get_permission_model_ids_from_request(self, request, view):
        return self._get_permission_model_ids_from_request_data(request, view.queryset.model, view) or \
               self._get_permission_model_ids_from_query_params(request.query_params, view.queryset.model)

    def _get_permission_model_ids_from_query_params(self, query_params, model):
        permission_model_attr = self.get_permission_model_attr(model)
        return query_params.getlist(permission_model_attr + 'Id')

    def _get_permission_model_ids_from_request_data(self, request, model, view):
        if not is_hal_content_type(request.content_type):
            return None

        permission_model_attr = self.get_permission_model_attr(model)
        if LINKS_FIELD_NAME in request.data and permission_model_attr in request.data[LINKS_FIELD_NAME]:
            return [get_id_from_detail_uri(request.data[LINKS_FIELD_NAME][permission_model_attr])]

        direct_parent = None
        direct_parent_id = None
        other_parent = None
        other_parent_id = None

        # there has to be a parent that holds the permission model in the parent lookups
        for kwarg_key in view.kwargs:
            if not kwarg_key.startswith(drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX):
                continue

            kwarg_key_without_prefix = kwarg_key.replace(drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX, '')
            if kwarg_key.endswith('__' + permission_model_attr):
                return [view.kwargs[kwarg_key]]
            elif '__' in kwarg_key:
                other_parent = kwarg_key_without_prefix.split('__')[0]
                if LINKS_FIELD_NAME in request.data and other_parent in request.data[LINKS_FIELD_NAME]:
                    other_parent_id = get_id_from_detail_uri(request.data[LINKS_FIELD_NAME][other_parent])
            else:
                direct_parent = kwarg_key_without_prefix
                direct_parent_id = view.kwargs[kwarg_key]

        permission_model_ids = self._get_permission_model_ids_from_parent(view.queryset.model, direct_parent, direct_parent_id)
        return permission_model_ids or self._get_permission_model_ids_from_parent(view.queryset.model, other_parent,
                                                                                  other_parent_id)

    def _get_permission_model_ids_from_parent(self, model, parent_field_name, parent_id):
        if not parent_field_name or not hasattr(model, parent_field_name):
            return None

        parent_attr = getattr(model, parent_field_name)
        parent_cls = parent_attr.field.rel.to
        return self.get_permission_model_ids_from_object(parent_cls.objects.get(id=parent_id))
