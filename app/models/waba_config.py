from django.db import models
from django.db.models import Q


class WabaConfig(models.Model):
    """Configuracion de cuenta WhatsApp (WABA) activa."""

    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(default=False, db_index=True)
    phone_id = models.CharField(max_length=50)
    access_token = models.TextField()
    verify_token = models.CharField(max_length=255, blank=True)
    api_base = models.CharField(max_length=255, default="https://graph.facebook.com")
    api_version = models.CharField(max_length=20, default="v22.0")
    business_id = models.CharField(max_length=50, blank=True)
    waba_id = models.CharField(max_length=50, blank=True)
    webhook_url = models.CharField(max_length=255, blank=True)
    interactive_enabled = models.BooleanField(default=False)
    flow_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "waba_config"
        constraints = [
            models.UniqueConstraint(
                condition=Q(active=True),
                fields=["active"],
                name="uniq_active_waba_config",
            )
        ]

    def __str__(self) -> str:
        status = "active" if self.active else "inactive"
        return f"{self.name} ({status})"
