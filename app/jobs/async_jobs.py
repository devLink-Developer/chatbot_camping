from __future__ import annotations

import logging
import threading
import time
import traceback
from typing import Callable, Dict, Optional

from django.conf import settings
from django.db import close_old_connections

from app.models.async_job import AsyncJob, GenericJobStatus

logger = logging.getLogger(__name__)

JOB_REGISTRY: Dict[str, Callable[[AsyncJob], None]] = {}
_THREADS: Dict[str, threading.Thread] = {}


def register_async_job(job_type: str, handler: Callable[[AsyncJob], None]) -> None:
    """Registra un handler disponible para el scheduler asincronico."""
    JOB_REGISTRY[job_type] = handler


def enqueue_job(
    job_type: str,
    *,
    name: Optional[str] = None,
    payload: Optional[dict] = None,
    user=None,
    wait_seconds: Optional[int] = None,
    dispatch: bool = True,
) -> AsyncJob:
    """Crea y despacha un job asincronico."""
    backend = getattr(settings, "ASYNC_BACKEND", "thread").lower()
    job = AsyncJob.objects.create(
        name=name or job_type,
        job_type=job_type,
        payload=payload or {},
        user=user if getattr(user, "pk", None) else None,
        backend=backend,
    )
    if dispatch:
        dispatch_async_job(job, backend=backend)
        timeout = wait_seconds if wait_seconds is not None else getattr(
            settings, "ASYNC_JOB_SYNC_TIMEOUT_SECONDS", 0
        )
        if timeout:
            wait_for_job(job, timeout)
    return job


def dispatch_async_job(job: AsyncJob, backend: Optional[str] = None) -> None:
    backend = (backend or getattr(settings, "ASYNC_BACKEND", "thread")).lower()
    if backend == "celery":
        try:
            from app.jobs.tasks import run_async_job
        except Exception:
            logger.exception("No se pudo importar la tarea Celery; usando backend thread.")
            backend = "thread"
        else:
            run_async_job.delay(str(job.pk))
            return

    thread = threading.Thread(
        target=_run_job_thread,
        args=(str(job.pk), backend),
        daemon=True,
        name=f"asyncjob-{job.pk}",
    )
    _THREADS[str(job.pk)] = thread
    thread.start()


def wait_for_job(job: AsyncJob, timeout: int) -> bool:
    """Bloquea hasta que el job finalice o se alcance el timeout."""
    if timeout <= 0:
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        job.refresh_from_db(fields=["status", "finished_at"])
        if job.status in AsyncJob.TERMINAL_STATES:
            return True
        time.sleep(0.5)
    return False


def execute_async_job(job_id: str, backend: Optional[str] = None) -> None:
    """Ejecuta el job identificado por job_id."""
    try:
        job = AsyncJob.objects.get(pk=job_id)
    except AsyncJob.DoesNotExist:
        logger.warning("AsyncJob %s no existe; omitiendo.", job_id)
        return
    if job.status in AsyncJob.TERMINAL_STATES:
        return

    handler = JOB_REGISTRY.get(job.job_type)
    if handler is None:
        job.mark_error(f"No hay handler registrado para {job.job_type}")
        logger.error("No handler for async job type %s", job.job_type)
        return

    job.mark_running(backend=backend or job.backend)
    try:
        handler(job)
    except Exception:
        logger.exception("Fallo el job asincronico %s", job_id)
        job.mark_error(traceback.format_exc())
    else:
        job.refresh_from_db(fields=["status"])
        if job.status == GenericJobStatus.RUNNING:
            job.mark_success("Completado.")


def _run_job_thread(job_id: str, backend: Optional[str]) -> None:
    close_old_connections()
    try:
        execute_async_job(job_id, backend=backend)
    finally:
        close_old_connections()
        _THREADS.pop(job_id, None)
