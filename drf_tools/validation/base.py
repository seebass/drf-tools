from abc import ABCMeta, abstractmethod

from django_tooling.exceptions import ValidationError


class FailedValidation():
    def __init__(self, code, details, msg):
        self.code = code
        self.details = details
        self.msg = msg
        if msg and details:
            self.msg = msg.format(**details)


class Validation(metaclass=ABCMeta):
    """
    Base class for all validations.
    The registered key is the app name plus the snake_case version of the class name.
    NameTooLong in secretobject will be available as secretobject_name_too_long
    """

    def __init__(self, fieldName=None):
        self.__fieldName = fieldName
        self.__failedValidations = list()

    @abstractmethod
    def _validate(self):
        pass

    def validate(self, raiseError=True):
        self._validate()
        if self.__failedValidations and raiseError:
            raise ValidationError([failedValidation.msg for failedValidation in self.__failedValidations], self.__fieldName)

    def _addFailure(self, code, details=None, msg=None):
        self.__failedValidations.append(FailedValidation(code, details, msg))

    def getFailedValidations(self):
        return self.__failedValidations
