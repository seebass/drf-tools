from django.db import models
from django_filters import FilterSet, BooleanFilter
from django_filters.filters import Filter
from django import forms


class ListFilterSet(FilterSet):
    """
    The filterset handles a list of values as filter, that are connected using the OR-Operator
    """

    def filter_queryset(self, queryset):
        for name, value in self.form.cleaned_data.items():

            # CUSTOM:START
            filter_ = self.filters[name]
            value_list = None

            if self.data:
                value_list = self.data.getlist(name)

            if value_list:
                filtered_qs = None
                for list_value in value_list:
                    if isinstance(filter_, BooleanFilter):
                        list_value = self._str_to_boolean(list_value)
                    if not filtered_qs:
                        filtered_qs = filter_.filter(queryset, list_value)
                    else:
                        filtered_qs |= filter_.filter(queryset, list_value)
                queryset = filtered_qs
            # CUSTOM:END

            assert isinstance(queryset, models.QuerySet), \
                "Expected '%s.%s' to return a QuerySet, but got a %s instead." \
                % (type(self).__name__, name, type(queryset).__name__)
        return queryset

    @staticmethod
    def _str_to_boolean(value):
        if value.lower() == "true":
            return True
        if value.lower() == "false":
            return False
        return value


class EnumFilter(Filter):
    def __init__(self, enum_type, *args, **kwargs):
        super(EnumFilter, self).__init__(*args, **kwargs)
        self.enum_type = enum_type

    field_class = forms.CharField

    def filter(self, qs, value):
        if value in ([], (), {}, None, ''):
            return qs
        enum_value = None
        for choice in self.enum_type:
            if choice.name == value or choice.value == value:
                enum_value = choice
                break
        if enum_value is None:
            raise ValueError("'{value}' is not a valid value for '{enum}'".format(value=value, enum=self.enum_type.__name__))
        return super(EnumFilter, self).filter(qs, enum_value)
