from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.db import models
from django.utils import timezone


class GenericJobStatus:
    """Estados posibles para los trabajos genéricos programados."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    CANCELED = "CANCELED"

    CHOICES = [
        (PENDING, "Pendiente"),
        (RUNNING, "En ejecución"),
        (SUCCESS, "Exitoso"),
        (ERROR, "Error"),
        (CANCELED, "Cancelado"),
    ]


class AsyncJob(models.Model):
    """Ejecuta trabajos que se despachan bajo demanda."""

    TERMINAL_STATES = {
        GenericJobStatus.SUCCESS,
        GenericJobStatus.ERROR,
        GenericJobStatus.CANCELED,
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    job_type = models.CharField(max_length=150)
    status = models.CharField(
        max_length=20,
        choices=GenericJobStatus.CHOICES,
        default=GenericJobStatus.PENDING,
    )
    payload = models.JSONField(blank=True, default=dict)
    result = models.JSONField(blank=True, null=True)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    message = models.TextField(blank=True)
    backend = models.CharField(max_length=30, blank=True)
    cancel_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    last_heartbeat_at = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="async_jobs",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created_at"]
        db_table = "async_jobs"
        indexes = [
            models.Index(fields=["status", "job_type"], name="asyncjob_status_idx"),
            models.Index(fields=["created_at"], name="asyncjob_created_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    @property
    def is_finished(self) -> bool:
        return self.status in self.TERMINAL_STATES

    def mark_running(self, backend: str | None = None) -> None:
        self.status = GenericJobStatus.RUNNING
        self.started_at = timezone.now()
        if backend:
            self.backend = backend
        self.save(update_fields=["status", "started_at", "backend"])

    def mark_success(self, message: str | None = None, result: dict | None = None) -> None:
        self.status = GenericJobStatus.SUCCESS
        self.finished_at = timezone.now()
        if message:
            self.message = message
        if result is not None:
            self.result = result
        self.progress = 100
        self.save(update_fields=["status", "finished_at", "message", "result", "progress"])

    def mark_error(self, message: str) -> None:
        self.status = GenericJobStatus.ERROR
        self.finished_at = timezone.now()
        self.message = message
        self.save(update_fields=["status", "finished_at", "message"])

    def request_cancel(self) -> None:
        if not self.is_finished and not self.cancel_requested:
            self.cancel_requested = True
            self.save(update_fields=["cancel_requested"])

    def mark_progress(self, percent: float, message: str | None = None) -> None:
        self.progress = max(0.0, min(100.0, float(percent)))
        update_fields = ["progress"]
        if message:
            self.message = message
            update_fields.append("message")
        self.save(update_fields=update_fields)

    def heartbeat(self) -> None:
        self.last_heartbeat_at = timezone.now()
        self.save(update_fields=["last_heartbeat_at"])


class GenericJobConfig(models.Model):
    """Configura trabajos genéricos integrados con APScheduler."""

    SCHEDULE_MANUAL = "MANUAL"
    SCHEDULE_DAILY = "DAILY"
    SCHEDULE_INTERVAL = "INTERVAL"
    SCHEDULE_CRON = "CRON"

    SCHEDULE_CHOICES = [
        (SCHEDULE_MANUAL, "Manual"),
        (SCHEDULE_DAILY, "Diario"),
        (SCHEDULE_INTERVAL, "Intervalo"),
        (SCHEDULE_CRON, "Cron"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    callable_path = models.CharField(
        max_length=255,
        help_text="Ruta dotted del callable o nombre registrado en app.jobs.scheduler_registry.",
    )
    callable_kwargs = models.JSONField(blank=True, default=dict)

    enabled = models.BooleanField(default=True)
    paused = models.BooleanField(default=False)
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_CHOICES, default=SCHEDULE_MANUAL)
    daily_time = models.TimeField(blank=True, null=True)
    interval_minutes = models.PositiveIntegerField(blank=True, null=True)
    cron_expression = models.CharField(max_length=120, blank=True)

    max_instances = models.PositiveIntegerField(default=1)
    coalesce = models.BooleanField(default=True)
    misfire_grace_seconds = models.PositiveIntegerField(default=60)

    cancel_requested = models.BooleanField(default=False)
    cancel_requested_at = models.DateTimeField(blank=True, null=True)

    chained_job = models.ForeignKey(
        "self",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="chained_dependents",
        help_text="Job a ejecutar automáticamente cuando este finaliza en SUCCESS.",
    )

    last_run_at = models.DateTimeField(blank=True, null=True)
    next_run_at = models.DateTimeField(blank=True, null=True)
    last_status = models.CharField(max_length=20, choices=GenericJobStatus.CHOICES, blank=True, null=True)
    last_message = models.TextField(blank=True)
    last_duration_ms = models.BigIntegerField(blank=True, null=True)

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="generic_jobs",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Job programado"
        verbose_name_plural = "Jobs programados"
        ordering = ["name"]
        db_table = "generic_job_configs"
        indexes = [
            models.Index(fields=["enabled", "paused", "schedule_type"], name="gjobcfg_sched_idx"),
            models.Index(fields=["last_run_at"], name="gjobcfg_last_run_idx"),
        ]

    def __str__(self) -> str:
        state = "ON" if self.enabled else "OFF"
        return f"{self.name} ({state})"

    def mark_cancel(self) -> None:
        self.cancel_requested = True
        self.cancel_requested_at = timezone.now()
        self.save(update_fields=["cancel_requested", "cancel_requested_at"])

    def clear_cancel(self) -> None:
        if self.cancel_requested:
            self.cancel_requested = False
            self.cancel_requested_at = None
            self.save(update_fields=["cancel_requested", "cancel_requested_at"])


class GenericJobRunLog(models.Model):
    """Historial de ejecuciones de trabajos genéricos."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    config = models.ForeignKey(
        GenericJobConfig,
        related_name="run_logs",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    job_type = models.CharField(max_length=50, default="generic", db_index=True)
    source_identifier = models.CharField(max_length=150, blank=True, db_index=True)
    triggered_by = models.CharField(max_length=50, default="scheduler")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="generic_job_runs",
    )
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=GenericJobStatus.CHOICES, default=GenericJobStatus.PENDING)
    message = models.TextField(blank=True)
    payload = models.JSONField(blank=True, default=dict)
    duration_ms = models.BigIntegerField(blank=True, null=True)
    run_identifier = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Ejecución de job"
        verbose_name_plural = "Ejecuciones de jobs"
        ordering = ["-started_at"]
        db_table = "generic_job_run_logs"
        indexes = [
            models.Index(fields=["status"], name="gjoblog_status_idx"),
            models.Index(fields=["started_at"], name="gjoblog_started_idx"),
            models.Index(fields=["job_type"], name="gjoblog_job_type_idx"),
            models.Index(fields=["source_identifier"], name="gjoblog_source_idx"),
        ]

    def mark_finished(
        self, status: str, message: str = "", finished_at: Optional[datetime] = None
    ) -> None:
        finished = finished_at or timezone.now()
        duration = None
        if self.started_at and finished:
            delta = finished - self.started_at
            duration = int(delta.total_seconds() * 1000)
        self.finished_at = finished
        self.status = status
        self.message = message
        self.duration_ms = duration
        self.save(update_fields=["finished_at", "status", "message", "duration_ms", "payload"])
