from datetime import datetime
import logging

from rest_framework import status
from rest_framework.mixins import RetrieveModelMixin, ListModelMixin, DestroyModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.relations import PrimaryKeyRelatedField
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.exceptions import ParseError
import drf_hal_json
from drf_hal_json.views import HalCreateModelMixin
from drf_nested_fields.views import CustomFieldsMixin, copy_meta_attributes

from drf_nested_routing.views import CreateNestedModelMixin, UpdateNestedModelMixin

from drf_tools import utils
from drf_tools.serializers import HalNestedFieldsModelSerializer, CsvSerializer, XlsxSerializer

logger = logging.getLogger(__name__)


def _add_parent_to_hal_request_data(request, parentKey):
    if not drf_hal_json.is_hal_content_type(request.content_type):
        return
    links = request.data.get('_links')
    if links and parentKey in links:
        return

    if not links:
        links = {}
        request.data['_links'] = links

    uriSplit = request.build_absolute_uri().split('/')
    if request.method == 'PUT':
        uriSplit = uriSplit[:-3]  # in case of PUT the id must be removed as well
    else:
        uriSplit = uriSplit[:-2]

    links[parentKey] = '/'.join(uriSplit) + '/'


class RestLoggingMixin(object):
    """Provides full logging of requests and responses"""

    def finalize_response(self, request, response, *args, **kwargs):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("{} {}".format(response.status_code, response.data))
        return super(RestLoggingMixin, self).finalize_response(request, response, *args, **kwargs)

    def initial(self, request, *args, **kwargs):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("{} {} {} {}".format(request.method, request.path, request.query_params, request.data))
        super(RestLoggingMixin, self).initial(request, *args, **kwargs)


class DefaultSerializerMixin(object):
    """
    If a view has no serializer_class specified, this mixin takes care of creating a default serializer_class that inherits
    HalNestedFieldsModelSerializer
    """

    def get_serializer_class(self):
        if not self.serializer_class:
            class DefaultSerializer(HalNestedFieldsModelSerializer):
                class Meta:
                    model = self.queryset.model

            self.serializer_class = DefaultSerializer

        return self.serializer_class


class HalNoLinksMixin(ListModelMixin):
    """
    For responses with a high amount of data, link generation can be switched of via query-param 'no_links'. Instead of links,
    simple ids are returned
    """

    def get_serializer_class(self):
        no_links = extract_boolean_from_query_params(self.get_serializer_context().get('request'), "no_links")
        if not no_links:
            return super(HalNoLinksMixin, self).get_serializer_class()

        self.always_included_fields = ["id"]
        serializer_class = super(HalNoLinksMixin, self).get_serializer_class()

        class HalNoLinksSerializer(serializer_class):
            serializer_related_field = PrimaryKeyRelatedField

            class Meta:
                pass

            copy_meta_attributes(serializer_class.Meta, Meta)

            @staticmethod
            def _is_link_field(field):
                return False

            @staticmethod
            def _get_links_serializer(model_cls, link_field_names):
                return None

        return HalNoLinksSerializer


class CreateModelMixin(CreateNestedModelMixin, HalCreateModelMixin):
    """
    Parents of nested resources are automatically added to the request content, so that they don't have to be defined twice
    (url and request content)
    """

    def _add_parent_to_request_data(self, request, parentKey, parentId):
        _add_parent_to_hal_request_data(request, parentKey)


class ReadModelMixin(HalNoLinksMixin, CustomFieldsMixin, RetrieveModelMixin, ListModelMixin):
    always_included_fields = ["id", api_settings.URL_FIELD_NAME]


class UpdateModelMixin(UpdateNestedModelMixin):
    """
    Additionally to the django-method it is checked if the resource exists and 404 is returned if not,
    instead of creating that resource

    Parents of nested resources are automatically added to the request content, so that they don't have to be defined twice
    (url and request content)
    """

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance is None:
            return Response("Resource with the given id/pk does not exist.", status=status.HTTP_404_NOT_FOUND)

        return super(UpdateModelMixin, self).update(request, *args, **kwargs)

    def _add_parent_to_request_data(self, request, parentKey, parentId):
        _add_parent_to_hal_request_data(request, parentKey)


class PartialUpdateOnlyMixin(object):
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @staticmethod
    def perform_update(serializer):
        serializer.save()


class BaseViewSet(RestLoggingMixin, DefaultSerializerMixin, GenericViewSet):
    pass


class ModelViewSet(CreateModelMixin, ReadModelMixin, UpdateModelMixin, DestroyModelMixin, BaseViewSet):
    pass


class FileUploadView(RestLoggingMixin, APIView):
    parser_classes = (MultiPartParser,)
    renderer_classes = (JSONRenderer,)

    def _get_file_and_name(self, request):
        file = self._get_file_from_request(request)
        return file.file, file.name

    def _get_file_bytes_and_name(self, request):
        file = self._get_file_from_request(request)
        return file.read(), file.name

    @staticmethod
    def _get_file_from_request(request):
        in_memory_upload_file = request.data.get('file')
        if not in_memory_upload_file or not in_memory_upload_file.file:
            raise ValueError("Mulitpart content must contain file.")
        return in_memory_upload_file


class XlsxImportView(FileUploadView):
    default_sheet_name = None
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

    def _get_xlsx_content_as_list_and_file_info(self, request):
        file_bytes, filename = self._get_file_bytes_and_name(request)
        sheetName = request.query_params.get('sheetName') or self.default_sheet_name
        return XlsxSerializer.deserialize(file_bytes, sheetName), filename, file_bytes


class CsvImportView(FileUploadView):
    media_type = 'text/csv'

    def _get_csv_content_as_list_and_file_info(self, request):
        file_bytes, filename = self._get_file_bytes_and_name(request)
        return CsvSerializer.deserialize(file_bytes), filename, file_bytes


def extract_int_from_query_params(request, key):
    value = request.query_params.get(key)
    if value:
        try:
            value = int(value)
        except ValueError:
            raise ParseError("Type of parameter '{}' must be 'int'".format(key))
    return value


def extract_datetime_from_query_params(request, key):
    value = request.query_params.get(key)
    if value:
        try:
            value = datetime.strptime(value, utils.DATETIME_FORMAT_ISO)
        except ValueError:
            raise ParseError(
                "Value of parameter '{}' has wrong format. Use '{}' instead".format(key, utils.DATETIME_FORMAT_ISO))
    return value


def extract_enum_from_query_params(request, key, enum_type):
    value = request.query_params.get(key)
    choices = [context.value for context in enum_type]
    if value:
        if value.upper() not in choices:
            raise ParseError("Value of query-parameter '{}' must be one out of {}".format(key, choices))
        return enum_type[value.upper()]

    return value


def extract_boolean_from_query_params(request, key):
    value = request.query_params.get(key)
    if not value:
        return None
    return value == 'true'


def get_instance_from_params(request, key, model_cls, optional=False):
    value = extract_int_from_query_params(request, key)
    if not value:
        if not optional:
            raise ParseError("Query-parameter '{}' must be set".format(key))
        else:
            return None

    return model_cls.objects.get(id=value)
