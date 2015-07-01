from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_tools.validation.request import ValidationRequest


class ValidationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        data = request.data
        request = ValidationRequest(data)
        return Response(request.validateAndGetResponseData(), 200)
