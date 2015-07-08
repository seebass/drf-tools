from functools import wraps


def with_debug(func):
    """Switch on DEBUG during a test (disabled by default). Useful for query logging."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        from django.conf import settings
        from django.db import connection

        settings.DEBUG = True
        connection.queries = []
        result = func(*args, **kwargs)
        settings.DEBUG = False
        return result

    return wrapper

def skip_abstract_test(func):
    def func_wrapper(self):
        if self.__class__.__subclasses__():
            return
        return func(self)

    return func_wrapper
