import logging
import os
import sys
from django.apps import AppConfig


logger = logging.getLogger(__name__)


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        try:
            from django.conf import settings as dj_settings

            skip_cmds = {
                "makemigrations",
                "migrate",
                "collectstatic",
                "shell",
                "createsuperuser",
                "loaddata",
                "dumpdata",
                "test",
            }
            if any(cmd in sys.argv for cmd in skip_cmds):
                return

            try:
                runserver = any("runserver" in (arg or "") for arg in sys.argv)
            except Exception:
                runserver = False

            is_reloader_child = os.environ.get("RUN_MAIN") == "true"
            should_start = (runserver and is_reloader_child) or (not dj_settings.DEBUG)

            if should_start and getattr(dj_settings, "ENABLE_SCHEDULER", True):
                from app.jobs.scheduler_bootstrap import initialize_scheduler

                initialize_scheduler()

            if should_start and getattr(dj_settings, "QUEUE_WORKER_ENABLED", True):
                from app.services.queue_worker import start_queue_worker

                start_queue_worker()
        except Exception:
            logger.exception("No se pudo inicializar scheduler de jobs.")
