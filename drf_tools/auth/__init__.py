from django.conf import settings

USER_SETTINGS = getattr(settings, "DRF_TOOLS", {})

PERMISSION_SERVICE = USER_SETTINGS.get("PERMISSION_SERVICE", None)
