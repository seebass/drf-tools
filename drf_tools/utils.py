from django.core.exceptions import ValidationError
from django.core.validators import URLValidator

DATETIME_FORMAT = '%d.%m.%Y %H:%M:%S'
DATETIME_FORMAT_ISO = '%Y-%m-%dT%H:%M:%S'

def get_id_from_detail_uri(uri):
    return int(uri.split('/')[-2])


def is_detail_uri(uri):
    try:
        get_id_from_detail_uri(uri)
        return True
    except ValueError:
        return False


def get_valid_uri(uri):
    if not uri:
        return None, True
    url = uri.strip()
    if not url.startswith("http"):
        url = 'http://' + url
    try:
        URLValidator()(url)
    except ValidationError:
        return None, False
    return url, True
