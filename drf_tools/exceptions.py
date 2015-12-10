import logging

from django.core.exceptions import ValidationError, ObjectDoesNotExist, PermissionDenied
from django.db import IntegrityError
from django.http import Http404
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def exception_handler(exc):
    headers = {}
    if isinstance(exc, APIException):
        if getattr(exc, 'auth_header', None):
            headers['WWW-Authenticate'] = exc.auth_header
        if getattr(exc, 'wait', None):
            headers['X-Throttle-Wait-Seconds'] = '%d' % exc.wait
            headers['Retry-After'] = '%d' % exc.wait
        status_code = exc.status_code
    elif isinstance(exc, (ValueError, ValidationError, IntegrityError)):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, PermissionDenied):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, (ObjectDoesNotExist, Http404)):
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR or logger.isEnabledFor(logging.DEBUG):
        logger.exception(str(exc))

    return Response(create_error_response_by_exception(exc), status=status_code, headers=headers)


def create_error_response_by_exception(exc):
    if hasattr(exc, 'messages'):
        messages = exc.messages
    else:
        messages = [str(exc)]
    code = 0
    if hasattr(exc, 'code'):
        code = exc.code
    return create_error_response(exc.__class__.__name__, messages, code)


def create_error_response(error_type, messages, code=0):
    error = dict()
    error['type'] = error_type
    error['messages'] = messages
    error['code'] = code
    return {'error': error}
