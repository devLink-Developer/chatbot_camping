"""
Bootstrap del scheduler APScheduler (adaptado de LiteCore).
"""

import logging
import os
from contextlib import suppress

from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.schedulers.background import BackgroundScheduler
from django.conf import settings
from django.db import connections

try:
    import fcntl  # type: ignore
except Exception:
    fcntl = None  # type: ignore

logger = logging.getLogger("jobs_scheduler")

scheduler = None
_lock_file = None
_LOCK_PATH = os.getenv("SCHEDULER_LOCK_PATH", "/tmp/chatbot_scheduler.lock")
_DB_LOCK_CONN = None
_DB_LOCK_IDS = (217728, 12173)


def _acquire_process_lock() -> bool:
    if fcntl is None:
        return True
    try:
        global _lock_file
        _lock_file = open(_LOCK_PATH, "a+")
        fcntl.flock(_lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_file.write(f"pid={os.getpid()}\n")
        _lock_file.flush()
        return True
    except Exception:
        with suppress(Exception):
            if _lock_file:
                _lock_file.close()
        return False


def _acquire_db_lock() -> bool:
    global _DB_LOCK_CONN
    try:
        if _DB_LOCK_CONN:
            return True
        conn = connections["default"]
        conn.ensure_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(%s, %s);", _DB_LOCK_IDS)
            locked = cursor.fetchone()[0]
        if locked:
            _DB_LOCK_CONN = conn
            return True
        return False
    except Exception:
        logger.warning("No se pudo adquirir advisory lock (se continua sin lock).", exc_info=True)
        return True


def _release_db_lock() -> None:
    global _DB_LOCK_CONN
    if not _DB_LOCK_CONN:
        return
    try:
        with _DB_LOCK_CONN.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock(%s, %s);", _DB_LOCK_IDS)
    except Exception:
        logger.warning("No se pudo liberar advisory lock.", exc_info=True)
    finally:
        try:
            _DB_LOCK_CONN.close()
        except Exception:
            pass
        _DB_LOCK_CONN = None


def initialize_scheduler():
    """Inicializa el scheduler APScheduler con configuración básica."""
    global scheduler

    if scheduler is None and not _acquire_process_lock():
        logger.info("Otro proceso mantiene el scheduler (%s).", _LOCK_PATH)
        return None
    if scheduler is None and not _acquire_db_lock():
        logger.info("Otro proceso mantiene advisory lock; no se inicializa.")
        return None

    if scheduler is not None:
        return scheduler

    executors = {"default": ThreadPoolExecutor(max_workers=8)}
    job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 30}
    scheduler = BackgroundScheduler(
        executors=executors,
        job_defaults=job_defaults,
        timezone=settings.TIME_ZONE,
    )

    try:
        from django_apscheduler.jobstores import DjangoJobStore

        scheduler.add_jobstore(DjangoJobStore(), "default")
        logger.info("DjangoJobStore agregado")
    except Exception as exc:
        logger.warning("No se pudo agregar DjangoJobStore: %s", exc)

    scheduler.start()
    logger.info("APScheduler inicializado")

    try:
        from app.jobs.generic_scheduler import (
            GenericSchedulerManager,
            set_generic_scheduler_manager,
            start_refresh_listener,
        )

        manager = GenericSchedulerManager(scheduler)
        set_generic_scheduler_manager(manager)
        start_refresh_listener()
        manager.refresh_all()
    except Exception:
        logger.exception("No se pudo inicializar el GenericScheduler")

    return scheduler


def get_scheduler():
    global scheduler
    if scheduler is None:
        initialize_scheduler()
    return scheduler


def shutdown_scheduler():
    global scheduler
    if scheduler is not None:
        try:
            scheduler.shutdown(wait=True)
            logger.info("APScheduler cerrado")
        except Exception as exc:
            logger.error("Error cerrando APScheduler: %s", exc, exc_info=True)
        finally:
            scheduler = None
            _release_db_lock()
