import time
from typing import Optional

from django.conf import settings

from app.models.waba_config import WabaConfig

_CACHE_TTL_SECONDS = 5
_cache_ts = 0.0
_cache_value: Optional[WabaConfig] = None


def get_active_waba_config() -> Optional[WabaConfig]:
    global _cache_ts, _cache_value
    now = time.time()
    if _cache_value is not None and (now - _cache_ts) < _CACHE_TTL_SECONDS:
        return _cache_value
    config = WabaConfig.objects.filter(active=True).first()
    _cache_value = config
    _cache_ts = now
    return config


def get_whatsapp_setting(field: str, default: str = "") -> str:
    config = get_active_waba_config()
    if config and getattr(config, field, None):
        return getattr(config, field)
    return getattr(settings, field, default)
