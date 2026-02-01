from django.contrib import admin
from django.conf import settings
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse, path
from django.utils.html import format_html, format_html_join
from django.utils.http import urlencode
from django.http import HttpResponseRedirect
from importlib import import_module
from croniter import croniter

from app.models.cliente import Cliente
from app.models.campana import Campana, CampanaTemplate
from app.models.campana_envio import CampanaEnvio
from app.models.mensaje import Mensaje
from app.models.async_job import AsyncJob, GenericJobConfig, GenericJobRunLog, GenericJobStatus
from app.jobs.async_jobs import dispatch_async_job
from app.jobs.scheduler_registry import list_jobs
from app.models.config import Config
from app.models.menu import Menu
from app.models.menu_option import MenuOption
from app.models.respuesta import Respuesta
from app.models.sesion import Sesion
from app.models.waba_config import WabaConfig
from app.services.flow_validator import validate_flow_for_menu


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "nombre",
        "alias_waba",
        "correo",
        "fecha_nacimiento",
        "marketing_opt_in",
        "mensajes_totales",
        "ultimo_contacto_ms",
        "updated_at",
        "ver_conversacion",
    )
    list_filter = ("activo",)
    search_fields = ("phone_number", "nombre", "alias_waba", "correo")
    ordering = ("-updated_at",)
    readonly_fields = (
        "phone_number",
        "primer_contacto_ms",
        "ultimo_contacto_ms",
        "mensajes_totales",
        "ultimo_mensaje",
        "created_at",
        "updated_at",
        "mensajes_recientes",
        "ver_conversacion",
    )
    fieldsets = (
        (
            "Cliente",
            {
                "fields": (
                    "phone_number",
                    "nombre",
                    "alias_waba",
                    "correo",
                    "fecha_nacimiento",
                    "direccion",
                    "marketing_opt_in",
                )
            },
        ),
        (
            "Actividad",
            {
                "fields": (
                    "mensajes_totales",
                    "primer_contacto_ms",
                    "ultimo_contacto_ms",
                    "ultimo_mensaje",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Conversacion",
            {"fields": ("mensajes_recientes", "ver_conversacion")},
        ),
    )

    def ver_conversacion(self, obj):
        url = reverse("admin:app_mensaje_changelist")
        query = urlencode({"phone_number__exact": obj.phone_number})
        return format_html('<a href="{}?{}">Ver mensajes</a>', url, query)

    ver_conversacion.short_description = "Conversacion"

    def mensajes_recientes(self, obj):
        mensajes = (
            Mensaje.objects.filter(phone_number=obj.phone_number)
            .order_by("-timestamp_ms")[:50]
        )
        mensajes = list(reversed(mensajes))
        if not mensajes:
            return "Sin mensajes"

        filas = []
        for msg in mensajes:
            icono = "<-" if msg.direccion == "in" else "->"
            cuerpo = (msg.contenido or "").strip()
            filas.append((icono, cuerpo))

        return format_html(
            '<div style="max-width:900px">'
            "{}"
            "</div>",
            format_html_join(
                "",
                '<div style="margin:4px 0;padding:6px 8px;border:1px solid #ddd;border-radius:6px">'
                "<strong>{}</strong> {}"
                "</div>",
                filas,
            ),
        )

    mensajes_recientes.short_description = "Mensajes recientes (ultimos 50)"


@admin.register(Sesion)
class SesionAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "nombre",
        "estado_actual",
        "activa",
        "ultimo_acceso_ms",
        "updated_at",
    )
    list_filter = ("activa",)
    search_fields = ("phone_number", "nombre")
    ordering = ("-updated_at",)


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    change_form_template = "admin/app/menu/change_form.html"
    list_display = (
        "id",
        "titulo",
        "is_main",
        "flow_id",
        "flow_status",
        "flow_valid",
        "parent",
        "orden",
        "activo",
        "updated_at",
    )
    list_filter = ("activo", "is_main", "flow_valid")
    search_fields = ("id", "titulo", "flow_id", "flow_name")
    ordering = ("orden", "id")
    readonly_fields = ("flow_last_checked_at", "flow_validation")
    actions = ["marcar_menu_principal", "validar_flow"]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.flow_id:
            try:
                validate_flow_for_menu(obj)
            except Exception as exc:
                self.message_user(
                    request,
                    f"No se pudo validar el flow automaticamente: {exc}",
                    level="warning",
                )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<path:object_id>/sync-flow/",
                self.admin_site.admin_view(self.sync_flow),
                name="app_menu_sync_flow",
            )
        ]
        return custom + urls

    def sync_flow(self, request, object_id):
        menu = self.get_object(request, object_id)
        if not menu:
            self.message_user(request, "Menu no encontrado.", level="warning")
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

        if not menu.flow_id:
            self.message_user(
                request,
                "El menu seleccionado no tiene flow_id.",
                level="warning",
            )
            return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

        resultado = validate_flow_for_menu(menu)
        if resultado.get("ok"):
            self.message_user(request, "Flow sincronizado correctamente.")
        else:
            self.message_user(
                request,
                "Flow sincronizado con advertencias. Revisar flow_validation.",
                level="warning",
            )
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/admin/"))

    @admin.action(description="Marcar como menu principal")
    def marcar_menu_principal(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Selecciona un solo menu.", level="warning")
            return
        Menu.objects.update(is_main=False)
        menu = queryset.first()
        menu.is_main = True
        menu.save(update_fields=["is_main"])
        self.message_user(request, f"Menu principal: {menu.titulo} ({menu.id})")

    @admin.action(description="Validar Flow del menu")
    def validar_flow(self, request, queryset):
        total = 0
        ok = 0
        for menu in queryset:
            total += 1
            resultado = validate_flow_for_menu(menu)
            if resultado.get("ok"):
                ok += 1
        if total == 1:
            menu = queryset.first()
            if menu and not menu.flow_id:
                self.message_user(request, "El menu seleccionado no tiene flow_id.", level="warning")
                return
        self.message_user(request, f"Validacion completada: {ok}/{total} OK.")


@admin.register(MenuOption)
class MenuOptionAdmin(admin.ModelAdmin):
    list_display = (
        "menu",
        "key",
        "label",
        "target_menu",
        "target_respuesta",
        "orden",
        "activo",
    )
    list_filter = ("activo",)
    search_fields = ("menu__id", "key", "label")
    ordering = ("menu__id", "orden")


@admin.register(Respuesta)
class RespuestaAdmin(admin.ModelAdmin):
    list_display = ("id", "categoria", "activo", "updated_at")
    list_filter = ("activo", "categoria")
    search_fields = ("id", "categoria", "contenido")
    ordering = ("id",)


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ("id", "seccion", "descripcion", "updated_at")
    list_filter = ("seccion",)
    search_fields = ("id", "seccion", "descripcion")
    ordering = ("id",)


@admin.register(WabaConfig)
class WabaConfigAdmin(admin.ModelAdmin):
    class WabaConfigForm(forms.ModelForm):
        access_token = forms.CharField(
            widget=forms.PasswordInput(render_value=True),
            required=True,
            help_text="Token de acceso de Meta (se guarda en BD).",
        )
        interactive_enabled = forms.BooleanField(
            required=False,
            label="Usar interactivos",
            help_text="Si esta activo, envia menus con mensajes interactivos.",
        )

        class Meta:
            model = WabaConfig
            fields = "__all__"

    form = WabaConfigForm
    list_display = ("name", "phone_id", "active", "interactive_enabled", "api_version", "updated_at")
    list_filter = ("active", "interactive_enabled", "api_version")
    search_fields = ("name", "phone_id", "business_id", "waba_id")
    ordering = ("-active", "name")
    actions = ["activar_config"]

    def save_model(self, request, obj, form, change):
        if obj.active:
            WabaConfig.objects.exclude(pk=obj.pk).update(active=False)
        super().save_model(request, obj, form, change)

    @admin.action(description="Activar esta configuracion")
    def activar_config(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, "Selecciona una sola configuracion.", level="warning")
            return
        WabaConfig.objects.update(active=False)
        config = queryset.first()
        config.active = True
        config.save(update_fields=["active"])
        self.message_user(request, f"Config activa: {config.name}")


@admin.register(Mensaje)
class MensajeAdmin(admin.ModelAdmin):
    list_display = (
        "phone_number",
        "direccion",
        "tipo",
        "contenido",
        "wa_message_id",
        "queue_status",
        "delivery_status",
        "timestamp_ms",
        "created_at",
    )
    list_filter = ("direccion", "tipo", "queue_status", "delivery_status", "phone_number", "created_at")
    search_fields = ("phone_number", "contenido", "wa_message_id")
    ordering = ("-created_at",)
    readonly_fields = (
        "phone_number",
        "nombre",
        "direccion",
        "tipo",
        "contenido",
        "wa_message_id",
        "timestamp_ms",
        "queue_status",
        "delivery_status",
        "delivery_timestamp_ms",
        "process_after_ms",
        "locked_at_ms",
        "processed_at_ms",
        "attempts",
        "error",
        "metadata_json",
        "created_at",
    )


@admin.register(AsyncJob)
class AsyncJobAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "job_type",
        "status_badge",
        "progress",
        "backend",
        "user",
        "created_at",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "job_type", "backend", "cancel_requested")
    search_fields = ("name", "job_type", "message", "payload")
    readonly_fields = (
        "status",
        "progress",
        "backend",
        "user",
        "payload",
        "result",
        "message",
        "cancel_requested",
        "created_at",
        "started_at",
        "finished_at",
        "last_heartbeat_at",
    )
    actions = ["request_cancel_action", "requeue_jobs"]

    def status_badge(self, obj):
        colors = {
            GenericJobStatus.PENDING: "secondary",
            GenericJobStatus.RUNNING: "info",
            GenericJobStatus.SUCCESS: "success",
            GenericJobStatus.ERROR: "danger",
            GenericJobStatus.CANCELED: "warning text-dark",
        }
        color = colors.get(obj.status, "secondary")
        return format_html('<span class="badge bg-{}">{}</span>', color, obj.status)

    status_badge.short_description = "Estado"

    @admin.action(description="Solicitar cancelacion")
    def request_cancel_action(self, request, queryset):
        for job in queryset:
            job.request_cancel()
        self.message_user(request, f"{queryset.count()} job(s) marcados para cancelacion.")

    @admin.action(description="Reencolar jobs finalizados")
    def requeue_jobs(self, request, queryset):
        count = 0
        for job in queryset:
            if job.status in AsyncJob.TERMINAL_STATES:
                job.status = GenericJobStatus.PENDING
                job.progress = 0
                job.message = ""
                job.started_at = None
                job.finished_at = None
                job.backend = getattr(settings, "ASYNC_BACKEND", "thread")
                job.save(
                    update_fields=[
                        "status",
                        "progress",
                        "message",
                        "started_at",
                        "finished_at",
                        "backend",
                    ]
                )
                dispatch_async_job(job)
                count += 1
        if count:
            self.message_user(request, f"Se reencolaron {count} job(s).")


@admin.register(GenericJobConfig)
class GenericJobConfigAdmin(admin.ModelAdmin):
    class GenericJobConfigForm(forms.ModelForm):
        callable_lookup = forms.ChoiceField(
            required=False,
            label="Callable registrado",
            help_text="Selecciona un callable registrado o deja vacio para ingresar la ruta manual.",
        )
        callable_kwargs = forms.JSONField(
            required=False,
            widget=forms.Textarea(attrs={"rows": 4, "class": "form-control monospace"}),
            help_text="JSON con kwargs adicionales para el callable.",
        )

        class Meta:
            model = GenericJobConfig
            fields = [
                "name",
                "description",
                "enabled",
                "paused",
                "callable_path",
                "callable_kwargs",
                "schedule_type",
                "daily_time",
                "interval_minutes",
                "cron_expression",
                "max_instances",
                "coalesce",
                "misfire_grace_seconds",
                "owner",
            ]
            widgets = {
                "description": forms.Textarea(attrs={"rows": 3}),
                "callable_path": forms.TextInput(attrs={"class": "form-control"}),
                "daily_time": forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
                "interval_minutes": forms.NumberInput(attrs={"class": "form-control"}),
                "cron_expression": forms.TextInput(attrs={"class": "form-control", "placeholder": "*/10 * * * *"}),
                "max_instances": forms.NumberInput(attrs={"class": "form-control"}),
                "misfire_grace_seconds": forms.NumberInput(attrs={"class": "form-control"}),
            }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            registry = list_jobs()
            choices = [("", "Selecciona un callable...")]
            choices += [(name, name) for name in sorted(registry.keys())]
            self.fields["callable_lookup"].choices = choices
            self.fields["callable_path"].required = False
            current_value = self.initial.get("callable_path") or getattr(self.instance, "callable_path", "")
            if current_value in registry:
                self.initial.setdefault("callable_lookup", current_value)

        def clean_callable_path(self):
            value = (self.cleaned_data.get("callable_path") or "").strip()
            if not value:
                return value
            registry = list_jobs()
            if value in registry:
                return value
            if "." not in value:
                raise ValidationError("Debe ser un nombre registrado o un dotted path valido.")
            module_path, func_name = value.rsplit(".", 1)
            try:
                module = import_module(module_path)
            except ImportError as exc:
                raise ValidationError(f"No se pudo importar el modulo: {exc}") from exc
            if not hasattr(module, func_name):
                raise ValidationError("La funcion indicada no existe en el modulo especificado.")
            return value

        def clean_callable_kwargs(self):
            data = self.cleaned_data.get("callable_kwargs")
            if data in (None, ""):
                return {}
            return data

        def clean(self):
            cleaned = super().clean()
            lookup = cleaned.get("callable_lookup")
            manual_value = (cleaned.get("callable_path") or "").strip()
            if lookup:
                cleaned["callable_path"] = lookup
            elif not manual_value:
                self.add_error(
                    "callable_path",
                    "Debes seleccionar un callable registrado o ingresar la ruta manual.",
                )
            schedule_type = cleaned.get("schedule_type")
            if schedule_type == GenericJobConfig.SCHEDULE_DAILY and not cleaned.get("daily_time"):
                self.add_error("daily_time", "Debes indicar la hora para la ejecucion diaria.")
            if schedule_type == GenericJobConfig.SCHEDULE_INTERVAL:
                minutes = cleaned.get("interval_minutes")
                if not minutes or minutes <= 0:
                    self.add_error("interval_minutes", "Ingresa un intervalo mayor a cero.")
            if schedule_type == GenericJobConfig.SCHEDULE_CRON:
                expr = cleaned.get("cron_expression")
                if not expr:
                    self.add_error("cron_expression", "Ingresa la expresion cron.")
                else:
                    try:
                        croniter(expr)
                    except Exception as exc:
                        self.add_error("cron_expression", f"Expresion cron invalida: {exc}")
            return cleaned

    form = GenericJobConfigForm
    list_display = (
        "name",
        "schedule_type",
        "enabled",
        "paused",
        "next_run_at",
        "last_run_at",
        "last_status",
    )
    list_filter = ("enabled", "paused", "schedule_type", "last_status")
    search_fields = ("name", "callable_path")
    ordering = ("name",)


@admin.register(GenericJobRunLog)
class GenericJobRunLogAdmin(admin.ModelAdmin):
    list_display = (
        "config",
        "status",
        "started_at",
        "finished_at",
        "duration_ms",
    )
    list_filter = ("status", "started_at")
    search_fields = ("config__name", "message", "source_identifier")
    ordering = ("-started_at",)


@admin.register(CampanaTemplate)
class CampanaTemplateAdmin(admin.ModelAdmin):
    list_display = ("nombre", "idioma", "activo", "updated_at")
    list_filter = ("activo", "idioma")
    search_fields = ("nombre", "idioma", "cuerpo")
    ordering = ("-updated_at",)


@admin.register(Campana)
class CampanaAdmin(admin.ModelAdmin):
    list_display = (
        "nombre",
        "tipo",
        "canal",
        "direccion_offset",
        "dias_offset",
        "hora_envio",
        "activo",
        "updated_at",
    )
    list_filter = ("activo", "tipo", "canal")
    search_fields = ("nombre", "descripcion", "template_nombre")
    ordering = ("-updated_at",)


@admin.register(CampanaEnvio)
class CampanaEnvioAdmin(admin.ModelAdmin):
    list_display = (
        "campana",
        "cliente",
        "estado",
        "programado_para",
        "enviado_en",
        "created_at",
    )
    list_filter = ("estado", "campana", "created_at")
    search_fields = ("cliente__phone_number", "campana__nombre", "error")
    ordering = ("-created_at",)
    readonly_fields = (
        "campana",
        "cliente",
        "estado",
        "programado_para",
        "enviado_en",
        "error",
        "payload_json",
        "created_at",
    )
