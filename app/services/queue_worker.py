import logging
import threading
import time

from django.conf import settings
from django.db import close_old_connections

from app.services.queue_processor import procesar_cola

logger = logging.getLogger(__name__)
_worker_thread = None
_stop_event = threading.Event()


def _worker_loop():
    interval = float(getattr(settings, "QUEUE_POLL_INTERVAL_SECONDS", 1.0))
    batch = int(getattr(settings, "QUEUE_BATCH_SIZE", 10))
    while not _stop_event.is_set():
        try:
            close_old_connections()
            procesar_cola(limit=batch)
        except Exception:
            logger.exception("Error en worker de cola.")
        _stop_event.wait(interval)


def start_queue_worker():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name="queue-worker",
        daemon=True,
    )
    _worker_thread.start()
    logger.info("Worker de cola iniciado.")


def stop_queue_worker():
    _stop_event.set()
