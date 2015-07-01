from abc import ABCMeta

from django.apps import apps
from importlib import import_module
from django.utils.module_loading import module_has_submodule
from django.utils.text import camel_case_to_spaces

from django_tooling.exceptions import ValidationError
from drf_tools.validation.base import Validation


class ValidationNotFoundException(ValidationError):
    def __init__(self, key):
        super().__init__(key)
        self.key = key


class ValidationRegistry:
    __VALIDATIONS_MODULE_NAME = 'validations'

    def __init__(self):
        self.__validations = {}
        self.__populate()

    def get(self, key):
        if key not in self.__validations:
            raise ValidationNotFoundException(key)
        return self.__validations[key]

    def __populate(self):
        """Loads all subclasses of Validation in the 'validations' module of apps in INSTALLED_APPs"""
        for app in apps.get_app_configs():
            if module_has_submodule(app.module, self.__VALIDATIONS_MODULE_NAME):
                moduleName = '%s.%s' % (app.name, self.__VALIDATIONS_MODULE_NAME)
                module = import_module(moduleName)
                moduleAttrs = (attr for attr in dir(module) if attr[0] != '_')
                for attrName in moduleAttrs:
                    cls = getattr(module, attrName)
                    # check if the attr is a class and of type validation
                    if not type(cls) in (type, ABCMeta) or not issubclass(cls, Validation) or cls is Validation:
                        continue
                    validationKey = self.__getValidationKeyFromClass(app, cls)
                    if validationKey in self.__validations:
                        raise Exception('Validation with name "{}" already exists.'.format(validationKey))
                    self.__validations[validationKey] = cls

    @staticmethod
    def __getValidationKeyFromClass(app, cls):
        validationKey = getattr(cls, 'key', None)
        if not validationKey:
            validationKey = camel_case_to_spaces(cls.__name__).replace(' ', '_')
        return "{}_{}".format(app.name, validationKey)


validationRegistry = ValidationRegistry()
