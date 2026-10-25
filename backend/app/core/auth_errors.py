"""Auth exceptions, mapped to HTTP responses in app.core.errors. Kept in
their own module (rather than defined in app.api.routes.auth) so
app.api.deps can raise them from get_current_user without a circular
import between deps and the auth route module.
"""


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass
