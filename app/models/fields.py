import json
from django.db import models


class LenientJSONField(models.JSONField):
    """JSONField that accepts already-decoded values from legacy schemas."""

    def from_db_value(self, value, expression, connection):
        if value is None or isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except TypeError:
            return value
