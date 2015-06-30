from django.core.validators import EMPTY_VALUES
from django_filters import FilterSet, BooleanFilter
from django_filters.filters import Filter
from django import forms
from django.utils import six


class ListFilterSet(FilterSet):
    """
    The filterset handles a list of values as filter, that are connected using the OR-Operator
    """

    @property
    def qs(self):
        if not hasattr(self, '_qs'):
            valid = self.is_bound and self.form.is_valid()

            if self.strict and self.is_bound and not valid:
                self._qs = self.queryset.none()
                return self._qs

            # start with all the results and filter from there
            qs = self.queryset.all()
            for name, filter_ in six.iteritems(self.filters):
                # CUSTOM:START
                value_list = None

                if valid and self.data:
                    value_list = self.data.getlist(name)

                if value_list:  # valid & clean data
                    filtered_qs = None
                    for value in value_list:
                        if isinstance(filter_, BooleanFilter):
                            value = self._str_to_boolean(value)

                        if not filtered_qs:
                            filtered_qs = filter_.filter(qs, value)
                        else:
                            filtered_qs |= filter_.filter(qs, value)
                    qs = filtered_qs
                    # CUSTOM:END

            if self._meta.order_by:
                order_field = self.form.fields[self.order_by_field]
                data = self.form[self.order_by_field].data
                ordered_value = None
                try:
                    ordered_value = order_field.clean(data)
                except forms.ValidationError:
                    pass

                if ordered_value in EMPTY_VALUES and self.strict:
                    ordered_value = self.form.fields[self.order_by_field].choices[0][0]

                if ordered_value:
                    qs = qs.order_by(*self.get_order_by(ordered_value))

            self._qs = qs

        return self._qs

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
