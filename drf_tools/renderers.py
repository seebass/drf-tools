from rest_framework.renderers import BaseRenderer as OriginalBaseRenderer

from drf_tools.serializers import ZipSerializer, CsvSerializer
from drf_tools.serializers import XlsxSerializer


class BaseFileRenderer(OriginalBaseRenderer):
    KWARGS_KEY_FILENAME = "filename"

    def _add_filename_to_response(self, renderer_context):
        filename = self._get_filename(renderer_context)
        if filename:
            renderer_context['response']['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)

    def _get_filename(self, renderer_context):
        filename = renderer_context['kwargs'].get(self.KWARGS_KEY_FILENAME)
        if filename and self.format and not filename.endswith('.' + self.format):
            filename += "." + self.format
        return filename


class CsvRenderer(BaseFileRenderer):
    media_type = "text/csv"
    format = "csv"
    separator = '\t'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        self._add_filename_to_response(renderer_context)
        return CsvSerializer.serialize(data, self.separator)


class XlsxRenderer(BaseFileRenderer):
    media_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    format = 'xlsx'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        self._add_filename_to_response(renderer_context)
        if not isinstance(data, list):
            return data

        return XlsxSerializer.serialize(data)


class ZipFileRenderer(BaseFileRenderer):
    """
    A zip file is created containing the given dict with filename->bytes
    """
    media_type = 'application/x-zip-compressed'
    format = 'zip'
    charset = None
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if not isinstance(data, dict) or renderer_context['response'].status_code != 200:
            return data
        self._add_filename_to_response(renderer_context)
        return ZipSerializer.serialize(data)


class AnyFileFromSystemRenderer(BaseFileRenderer):
    """
    Given the full file path, the file is opened, read and returned
    """
    media_type = '*/*'
    render_style = 'binary'

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context['response'].status_code != 200:
            return data
        self._add_filename_to_response(renderer_context)
        if isinstance(data, str):
            with open(data, "rb") as file:
                return file.read()
        return data
