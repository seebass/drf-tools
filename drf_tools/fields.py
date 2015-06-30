from rest_framework.fields import CharField


class FilenameField(CharField):
    def to_representation(self, value):
        value = super(FilenameField, self).to_representation(value)
        if value:
            value = value.split("/")[-1]
        return value
