"""Generic APScheduler integration for configurable jobs (LiteCore style)."""

from __future__ import annotations

import builtins
import logging
import select
import threading
import time
import uuid
from datetime import timedelta
from importlib import import_module
from typing import Any, Callable, Dict, Optional

from apscheduler.jobstores.base import JobLookupError
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
from django.db import connection, connections
from django.utils import timezone

try:  # pragma: no cover - optional during tests
    import psycopg
except Exception:  # pragma: no cover
    psycopg = None  # type: ignore

from app.jobs.scheduler_registry import list_jobs
from app.models.async_job import GenericJobConfig, GenericJobRunLog, GenericJobStatus

logger = logging.getLogger("generic_jobs")
REFRESH_CHANNEL = "generic_scheduler_refresh"


class GenericJobCancelled(Exception):
    """Raised by jobs when a cooperative cancellation is requested."""


class GenericJobContext:
    """Runtime context passed to job callables for cooperative controls."""

    def __init__(self, config_id: uuid.UUID, run_log_id: uuid.UUID):
        self.config_id = config_id
        self.run_log_id = run_log_id
        self._logger = logger.getChild(f"job[{config_id}]")

    def should_cancel(self) -> bool:
        return (
            GenericJobConfig.objects.filter(pk=self.config_id, cancel_requested=True)
            .values_list("cancel_requested", flat=True)
            .first()
            is True
        )

    def log(self, message: str, level: int = logging.INFO) -> None:
        self._logger.log(level, message)

    def update_message(self, message: str) -> None:
        GenericJobConfig.objects.filter(pk=self.config_id).update(
            last_message=message, updated_at=timezone.now()
        )


class GenericSchedulerManager:
    """Handles scheduling lifecycle for GenericJobConfig entries."""

    job_prefix = "generic_job_"

    def __init__(self, scheduler: BackgroundScheduler):
        self.scheduler = scheduler

    def _create_trigger(self, config: GenericJobConfig):
        tz = timezone.get_current_timezone()
        if config.schedule_type == GenericJobConfig.SCHEDULE_DAILY:
            if not config.daily_time:
                logger.warning("Config %s: DAILY sin hora configurada", config.name)
                return None
            return CronTrigger(
                hour=config.daily_time.hour,
                minute=config.daily_time.minute,
                timezone=tz,
            )
        if config.schedule_type == GenericJobConfig.SCHEDULE_INTERVAL:
            if not config.interval_minutes or config.interval_minutes <= 0:
                logger.warning("Config %s: INTERVAL invalido", config.name)
                return None
            return IntervalTrigger(minutes=config.interval_minutes, timezone=tz)
        if config.schedule_type == GenericJobConfig.SCHEDULE_CRON:
            cron_value = config.cron_expression
            if not cron_value:
                logger.warning("Config %s: CRON sin expresion", config.name)
                return None
            try:
                return CronTrigger.from_crontab(cron_value, timezone=tz)
            except Exception as exc:
                logger.error("Config %s: cron invalido (%s)", config.name, exc)
                return None
        return None

    def _job_id(self, config_id: uuid.UUID | str) -> str:
        return f"{self.job_prefix}{config_id}"

    def _update_next_run(self, config: GenericJobConfig) -> None:
        job = self.scheduler.get_job(self._job_id(config.id))
        next_run = job.next_run_time if job else None
        GenericJobConfig.objects.filter(pk=config.pk).update(next_run_at=next_run)

    def schedule_job(self, config: GenericJobConfig) -> bool:
        if (
            not config.enabled
            or config.schedule_type == GenericJobConfig.SCHEDULE_MANUAL
            or config.paused
        ):
            self.unschedule_job(config)
            return False

        trigger = self._create_trigger(config)
        if not trigger:
            self.unschedule_job(config)
            return False

        job_id = self._job_id(config.id)
        try:
            self.scheduler.remove_job(job_id)
        except JobLookupError:
            pass

        self.scheduler.add_job(
            execute_generic_job,
            trigger=trigger,
            args=[str(config.id)],
            kwargs={"triggered_by": "scheduler"},
            id=job_id,
            name=f"{config.name}",
            replace_existing=True,
            max_instances=config.max_instances,
            coalesce=config.coalesce,
            misfire_grace_time=config.misfire_grace_seconds,
        )
        GenericJobConfig.objects.filter(pk=config.pk).update(paused=False)
        self._update_next_run(config)
        logger.info("Config %s programada", config.name)
        return True

    def unschedule_job(self, config: GenericJobConfig) -> None:
        job_id = self._job_id(config.id)
        try:
            self.scheduler.remove_job(job_id)
        except JobLookupError:
            pass
        GenericJobConfig.objects.filter(pk=config.pk).update(next_run_at=None)
        logger.info("Config %s desprogramada", config.name)

    def pause_job(self, config: GenericJobConfig) -> None:
        self.unschedule_job(config)
        GenericJobConfig.objects.filter(pk=config.pk).update(paused=True)
        logger.info("Config %s pausada", config.name)

    def resume_job(self, config: GenericJobConfig) -> None:
        GenericJobConfig.objects.filter(pk=config.pk).update(paused=False)
        self.schedule_job(config)

    def refresh_all(self) -> Dict[str, int]:
        existing_jobs = [
            job.id
            for job in self.scheduler.get_jobs()
            if job.id.startswith(self.job_prefix)
        ]
        for job_id in existing_jobs:
            try:
                self.scheduler.remove_job(job_id)
            except JobLookupError:
                pass

        configs = GenericJobConfig.objects.filter(enabled=True)
        scheduled = 0
        failed = 0
        for config in configs:
            if self.schedule_job(config):
                scheduled += 1
            else:
                failed += 1
        return {
            "total_configs": configs.count(),
            "scheduled": scheduled,
            "failed": failed,
            "removed": len(existing_jobs),
        }

    def trigger_now(
        self,
        config: GenericJobConfig,
        triggered_by: str = "manual",
        user_id: Optional[str] = None,
        extra_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        run_date = timezone.now()
        job_id = f"{self._job_id(config.id)}_manual_{uuid.uuid4()}"
        kwargs = {"triggered_by": triggered_by, "user_id": user_id, "runtime_kwargs": extra_kwargs or {}}
        self.scheduler.add_job(
            execute_generic_job,
            trigger=DateTrigger(run_date=run_date, timezone=timezone.get_current_timezone()),
            args=[str(config.id)],
            kwargs=kwargs,
            id=job_id,
            name=f"{config.name} (manual)",
            replace_existing=False,
            max_instances=config.max_instances,
            coalesce=False,
            misfire_grace_time=config.misfire_grace_seconds,
        )

    def cancel_job(self, config: GenericJobConfig) -> None:
        config.mark_cancel()
        logger.info("Cancelacion solicitada para config %s", config.name)


def execute_generic_job(
    config_id: str,
    *,
    triggered_by: str = "scheduler",
    user_id: Optional[str] = None,
    runtime_kwargs: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Wrapper invoked by APScheduler to execute a configured job."""
    try:
        config = GenericJobConfig.objects.get(pk=config_id)
    except GenericJobConfig.DoesNotExist:
        logger.error("Job config %s no encontrada", config_id)
        return None

    if not config.enabled and triggered_by == "scheduler":
        logger.info("Job %s deshabilitado, se omite ejecucion programada", config.name)
        return None

    if config.paused and triggered_by == "scheduler":
        logger.info("Job %s pausado, se omite ejecucion programada", config.name)
        return None

    GenericJobConfig.objects.filter(pk=config.pk).update(cancel_requested=False, cancel_requested_at=None)

    stale_minutes = getattr(settings, "GENERIC_JOB_STALE_MINUTES", 15)
    if stale_minutes and stale_minutes > 0:
        now = timezone.now()
        stale_cutoff = now - timedelta(minutes=stale_minutes)
        stale_qs = GenericJobRunLog.objects.filter(
            config=config,
            status=GenericJobStatus.RUNNING,
            started_at__lt=stale_cutoff,
        )
        if stale_qs.exists():
            msg = f"Ejecucion marcada como ERROR por exceder {stale_minutes} min."
            for run in stale_qs:
                run.mark_finished(status=GenericJobStatus.ERROR, message=msg, finished_at=now)
            logger.warning(
                "Se marcaron ejecuciones RUNNING como ERROR por antiguedad (job=%s, minutos=%s)",
                config.name,
                stale_minutes,
            )

    if GenericJobRunLog.objects.filter(config=config, status=GenericJobStatus.RUNNING).exists():
        now = timezone.now()
        msg = "Ejecucion omitida: ya hay otra instancia en curso."
        skip_log = GenericJobRunLog.objects.create(
            config=config,
            job_type="generic",
            source_identifier=str(config.id),
            triggered_by=triggered_by,
            user_id=user_id,
            started_at=now,
            status=GenericJobStatus.RUNNING,
        )
        skip_log.mark_finished(status=GenericJobStatus.SUCCESS, message=msg, finished_at=now)
        GenericJobConfig.objects.filter(pk=config.pk).update(
            last_run_at=now,
            last_status=GenericJobStatus.SUCCESS,
            last_message=msg,
            last_duration_ms=0,
        )
        logger.info("Job %s omitido por ejecucion simultanea", config.name)
        return None

    started_at = timezone.now()
    run_log = GenericJobRunLog.objects.create(
        config=config,
        job_type="generic",
        source_identifier=str(config.id),
        triggered_by=triggered_by,
        user_id=user_id,
        started_at=started_at,
        status=GenericJobStatus.RUNNING,
    )

    GenericJobConfig.objects.filter(pk=config.pk).update(
        last_run_at=started_at,
        last_status=GenericJobStatus.RUNNING,
        last_message="",
        last_duration_ms=None,
    )

    context = GenericJobContext(config.id, run_log.id)

    kwargs = dict(config.callable_kwargs or {})
    if runtime_kwargs:
        kwargs.update(runtime_kwargs)
    kwargs.setdefault("job_context", context)
    kwargs.setdefault("triggered_by", triggered_by)

    status = GenericJobStatus.SUCCESS
    message = ""

    try:
        func = _resolve_callable(config.callable_path)
        result = func(**kwargs)
        if result is not None:
            message = str(result)
    except GenericJobCancelled as exc:
        status = GenericJobStatus.CANCELED
        message = str(exc) or "Ejecucion cancelada."
        logger.info("Job %s cancelado: %s", config.name, message)
    except Exception as exc:
        status = GenericJobStatus.ERROR
        message = str(exc)
        logger.exception("Job %s fallo: %s", config.name, exc)
    finally:
        run_log.mark_finished(status=status, message=message)
        GenericJobConfig.objects.filter(pk=config.pk).update(
            last_status=status,
            last_message=message,
            last_duration_ms=run_log.duration_ms,
            next_run_at=_get_next_run_time(config.id),
        )

    if status == GenericJobStatus.SUCCESS and config.chained_job_id and config.chained_job_id != config.id:
        try:
            chained = (
                GenericJobConfig.objects.filter(pk=config.chained_job_id, enabled=True, paused=False).first()
            )
            if chained:
                logger.info("Disparando job encadenado %s -> %s", config.name, chained.name)
                execute_generic_job(str(chained.id), triggered_by=f"chained:{config.id}")
        except Exception:
            logger.exception("No se pudo disparar el job encadenado desde %s", config.name)

    return None


def _resolve_callable(path: str) -> Callable[..., Any]:
    registry = list_jobs()
    if path in registry:
        return registry[path]
    if "." not in path:
        raise ValueError(f"Callable '{path}' no registrado.")
    module_path, func_name = path.rsplit(".", 1)
    module = import_module(module_path)
    func = getattr(module, func_name, None)
    if func is None:
        raise ValueError(f"Callable '{path}' no encontrado.")
    return func


def _get_next_run_time(config_id: uuid.UUID) -> Optional[timezone.datetime]:
    manager = get_generic_scheduler_manager()
    if not manager:
        return None
    job = manager.scheduler.get_job(f"{manager.job_prefix}{config_id}")
    return job.next_run_time if job else None


def get_generic_scheduler_manager() -> Optional[GenericSchedulerManager]:
    return getattr(builtins, "generic_scheduler_manager", None)


def set_generic_scheduler_manager(manager: GenericSchedulerManager) -> None:
    builtins.generic_scheduler_manager = manager


def request_scheduler_refresh(reason: str = "manual") -> None:
    """Envía un notify a Postgres para refrescar la programación."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_notify(%s, %s)", [REFRESH_CHANNEL, reason])
    except Exception:
        logger.exception("No se pudo solicitar refresh del scheduler (razon=%s)", reason)


def start_refresh_listener() -> None:
    """Escucha pg_notify y gatilla refresh (si psycopg está disponible)."""
    if getattr(builtins, "generic_scheduler_refresh_thread", None):
        return
    if psycopg is None:
        logger.warning("psycopg no disponible; no se inicializa listener de refresh")
        return

    thread = threading.Thread(target=_refresh_listener_loop, name="generic-scheduler-refresh", daemon=True)
    builtins.generic_scheduler_refresh_thread = thread
    thread.start()


def _refresh_listener_loop() -> None:
    db_settings = connections.databases.get("default", {})
    conn_params = {
        "host": db_settings.get("HOST") or None,
        "port": db_settings.get("PORT") or None,
        "dbname": db_settings.get("NAME"),
        "user": db_settings.get("USER") or None,
        "password": db_settings.get("PASSWORD") or None,
    }
    while True:
        try:
            assert psycopg is not None
            with psycopg.connect(**conn_params) as conn:
                conn.autocommit = True
                with conn.cursor() as cur:
                    cur.execute(f"LISTEN {REFRESH_CHANNEL};")
                    logger.info("Listener esperando notificaciones en %s", REFRESH_CHANNEL)

                    def _handle_refresh(notify) -> None:
                        logger.info("Notificacion de refresh: %s", notify.payload)
                        manager = get_generic_scheduler_manager()
                        if manager:
                            try:
                                stats = manager.refresh_all()
                                logger.info("Scheduler refrescado: %s", stats)
                            except Exception:
                                logger.exception("Error refrescando scheduler tras notificacion")
                        else:
                            logger.warning("No hay GenericSchedulerManager al procesar refresh")

                    if hasattr(conn, "poll"):
                        while True:
                            if select.select([conn], [], [], 60)[0]:
                                conn.poll()
                                while conn.notifies:
                                    _handle_refresh(conn.notifies.pop(0))
                            else:
                                conn.poll()
                    else:
                        notifications = conn.notifies()
                        while True:
                            try:
                                notify = next(notifications)
                            except StopIteration:
                                continue
                            _handle_refresh(notify)
        except Exception:
            logger.exception("Fallo listener de refresh; reintentando en 5s")
            time.sleep(5)
