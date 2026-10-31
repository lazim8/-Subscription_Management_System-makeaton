import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class StrongPasswordValidator:
    """
    Validates that a password satisfies the Brightloop security requirements:
    - More than 8 characters (> 8 characters, i.e. 9 or more characters)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one special character
    """
    def validate(self, password, user=None):
        if len(password) <= 8:
            raise ValidationError(
                _("Password must be more than 8 characters long (at least 9 characters)."),
                code='password_too_short',
            )
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter."),
                code='password_no_lower',
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\/`~]', password):
            raise ValidationError(
                _("Password must contain at least one special character (!@#$%^&*...)."),
                code='password_no_special',
            )

    def get_help_text(self):
        return _(
            "Your password must be more than 8 characters, contain at least one uppercase letter, "
            "one lowercase letter, and one special character."
        )
