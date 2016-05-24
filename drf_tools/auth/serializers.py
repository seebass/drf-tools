from django.contrib.auth import get_user_model
from rest_framework.fields import EmailField
from rest_framework.fields import BooleanField

from drf_tools.serializers import HalNestedFieldsModelSerializer


class UserSerializer(HalNestedFieldsModelSerializer):
    isSuperAdmin = BooleanField(source="is_superuser", read_only=True)
    isSuperReader = BooleanField(source="is_staff", read_only=True)
    email = EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'password', 'first_name', 'last_name', 'isSuperAdmin', 'isSuperReader')
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = ('id',)
