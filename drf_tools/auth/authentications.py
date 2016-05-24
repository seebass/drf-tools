from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.authentication import BasicAuthentication

User = get_user_model()


class QuietBasicAuthentication(BasicAuthentication):
    """
    This is basically a BasicAuthentication. The only difference ist the returned authorization header in case of an
    incorrect login. If the default header is returned, the browser would force the user to enter the credentials in a
    pop-up window, which is not wanted in case of a frontend-app with built-in login form.
    This Authentication works well with SessionAuthentication. Once the user is logged in, this should NOT be used as a
    substitute for SessionAuthentication, which uses the django session cookie, rather it can check credentials before
    a session cookie has been granted.
    """

    def authenticate_header(self, request):
        return 'xBasic realm="%s"' % self.www_authenticate_realm


class EmailAuthBackend(object):
    """
    Email Authentication Backend

    Allows a user to sign in using an email/password pair rather than
    a username/password pair.
    """

    def authenticate(self, username=None, password=None):
        """ Authenticate a user based on email address as the user name. """
        try:
            user = User.objects.get(Q(email=username) | Q(username=username))
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        """ Get a User object from the user_id. """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
