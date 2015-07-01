from abc import ABCMeta
from urllib.parse import urlsplit

from django.conf import settings
from django.core import urlresolvers
import drf_nested_routing
from rest_framework.exceptions import ParseError

from drf_tools.validation.registry import validationRegistry


class ValidationRequest(metaclass=ABCMeta):
    def __init__(self, requestData):
        data = self.__getData(requestData)
        key = self.__getKey(requestData)
        ValidationClass = validationRegistry.get(key)
        self.__validation = ValidationClass(data=data)

    def validateAndGetResponseData(self):
        self.__validation.validate(raiseError=False)
        valid = len(self.__validation.getFailedValidations()) == 0
        responseData = {'valid': valid}
        if not valid:
            failedValidationsNative = list()
            for failedValidation in self.__validation.getFailedValidations():
                failedValidationsNative.append(failedValidation.__dict__)
            responseData['failedValidations'] = failedValidationsNative
        return responseData

    @staticmethod
    def __getKey(requestData):
        if '_key' not in requestData:
            raise ParseError('Missing required field "_key".')
        return requestData.pop('_key')

    def __getData(self, requestData):
        if '_links' in requestData:
            urlconf = settings.ROOT_URLCONF
            urlresolvers.set_urlconf(urlconf)
            resolver = urlresolvers.RegexURLResolver(r'^/', urlconf)
            for prop, url in requestData['_links'].items():
                requestData[prop] = self.__getObjectForUrl(url, resolver)
            del requestData['_links']
        return requestData

    @staticmethod
    def __getObjectForUrl(url, resolver):
        if isinstance(url, dict):
            if '_links' in url and 'self' in url['_links']:
                url = url['_links']['self']
            else:
                raise ParseError('Expected a URL but found an object in _links')
        pathInfo = urlsplit(url).path
        resolver_match = resolver.resolve(pathInfo)
        callback, callback_args, callback_kwargs = resolver_match
        ModelCls = callback.cls.queryset.model
        lookups = {}
        for k, v in callback_kwargs.items():
            if k.startswith(drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX):
                k = k[len(drf_nested_routing.PARENT_LOOKUP_NAME_PREFIX):]
            lookups[k] = v
        queryset = ModelCls.objects.filter(**lookups)
        return queryset.first()
