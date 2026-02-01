import json
import time
from unittest.mock import patch

from django.test import TestCase, override_settings

from app.models.cliente import Cliente
from app.models.config import Config
from app.models.menu import Menu
from app.models.menu_option import MenuOption
from app.models.mensaje import Mensaje
from app.models.respuesta import Respuesta
from app.models.sesion import Sesion
from app.services.gestor_contenido import GestorContenido
from app.services.queue_processor import (
    procesar_inbound_pendientes,
    procesar_outbound_pendientes,
)
from app import views


TEST_DB = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


@override_settings(DATABASES=TEST_DB)
class ContenidoFormattingTests(TestCase):
    def test_formatear_respuesta_elimina_navegacion_duplicada(self):
        respuesta = Respuesta.objects.create(
            id="R_DUP",
            categoria="test",
            contenido="Linea 1\n0️⃣ Volver al menú principal\n#️⃣ Volver atrás",
        )
        resultado = GestorContenido.formatear_respuesta(respuesta)
        assert resultado.count("Volver al menu principal") == 1
        assert resultado.count("Volver atras") == 1

    def test_formatear_menu_elimina_navegacion_duplicada(self):
        menu = Menu.objects.create(
            id="M_DUP",
            titulo="Menu X",
            contenido="Linea A\n0️⃣ Volver al menú principal\n#️⃣ Volver atrás",
        )
        resultado = GestorContenido.formatear_menu(menu)
        assert resultado.count("Volver al menu principal") == 1
        assert resultado.count("Volver atras") == 1


@override_settings(
    DATABASES=TEST_DB,
    WHATSAPP_VERIFY_TOKEN="test-token",
    SESSION_TIMEOUT_SECONDS=1,
)
class WebhookFlowTests(TestCase):
    def setUp(self):
        Config.objects.create(
            id="mensaje_bienvenida",
            seccion="mensajes",
            valor={"contenido": "Bienvenida"},
        )
        Config.objects.create(
            id="mensaje_error_sesion",
            seccion="mensajes",
            valor={"contenido": "Sesion expirada"},
        )

        menu_principal = Menu.objects.create(id="0", titulo="Menu", contenido="")
        menu_sub = Menu.objects.create(id="1", titulo="Submenu", contenido="")
        respuesta_1 = Respuesta.objects.create(
            id="R1", categoria="info", contenido="Respuesta 1"
        )
        respuesta_2 = Respuesta.objects.create(
            id="R2",
            categoria="info",
            contenido="Contenido con nav\n0️⃣ Volver al menú principal\n#️⃣ Volver atrás",
        )

        MenuOption.objects.create(
            menu=menu_principal,
            key="1",
            label="Opcion 1",
            target_respuesta=respuesta_1,
            orden=1,
        )
        MenuOption.objects.create(
            menu=menu_principal,
            key="2",
            label="Submenu",
            target_menu=menu_sub,
            orden=2,
        )
        MenuOption.objects.create(
            menu=menu_sub,
            key="A",
            label="Opcion A",
            target_respuesta=respuesta_2,
            orden=1,
        )

    def _payload(self, texto="hola", numero="5491112345678", tipo="text", message_id: str | None = None):
        message_id = message_id or f"wamid.test.{time.time_ns()}"
        message = {
            "id": message_id,
            "from": numero,
            "timestamp": str(int(time.time())),
            "type": tipo,
        }
        if tipo == "text":
            message["text"] = {"body": texto}

        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [message],
                                "contacts": [{"profile": {"name": "Tester"}}],
                            }
                        }
                    ]
                }
            ]
        }

    def _payload_sin_mensajes(self):
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [],
                                "contacts": [{"profile": {"name": "Tester"}}],
                            }
                        }
                    ]
                }
            ]
        }

    def _payload_multi(self):
        base_ts = int(time.time())
        messages = [
            {
                "id": "wamid.test.1",
                "from": "5491112345678",
                "timestamp": str(base_ts),
                "type": "text",
                "text": {"body": "hola"},
            },
            {
                "id": "wamid.test.2",
                "from": "5491112345678",
                "timestamp": str(base_ts + 1),
                "type": "text",
                "text": {"body": "1"},
            },
        ]
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": messages,
                                "contacts": [{"profile": {"name": "Tester"}}],
                            }
                        }
                    ]
                }
            ]
        }

    def _payload_interactive(self, reply_id: str = "1", reply_title: str = "Servicios"):
        message_id = f"wamid.test.{time.time_ns()}"
        message = {
            "id": message_id,
            "from": "5491112345678",
            "timestamp": str(int(time.time())),
            "type": "interactive",
            "interactive": {
                "list_reply": {"id": reply_id, "title": reply_title},
            },
        }
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "messages": [message],
                                "contacts": [{"profile": {"name": "Tester"}}],
                            }
                        }
                    ]
                }
            ]
        }

    def test_webhook_verificacion_ok(self):
        resp = self.client.get(
            "/webhook/mensajes?hub.mode=subscribe&hub.challenge=123&hub.verify_token=test-token"
        )
        assert resp.status_code == 200
        assert resp.content == b"123"

    def test_webhook_verificacion_falla(self):
        resp = self.client.get(
            "/webhook/mensajes?hub.mode=subscribe&hub.challenge=123&hub.verify_token=bad"
        )
        assert resp.status_code == 403

    def test_webhook_json_invalido(self):
        resp = self.client.post(
            "/webhook/mensajes",
            data="{no-json",
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_payload_sin_mensajes(self):
        resp = self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload_sin_mensajes()),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert Mensaje.objects.count() == 0

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_payload_multi_messages(self, mocked_send, mocked_read):
        resp = self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload_multi()),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert Mensaje.objects.filter(direccion="in").count() == 2

        procesar_inbound_pendientes(limit=10)
        assert Mensaje.objects.filter(direccion="out").count() == 2

        procesar_outbound_pendientes(limit=10)
        assert mocked_send.call_count == 2

    def test_status_update_delivered(self):
        Mensaje.objects.create(
            phone_number="+5491112345678",
            nombre="Tester",
            direccion="out",
            tipo="text",
            contenido="Respuesta",
            wa_message_id="wamid.status",
            timestamp_ms=int(time.time() * 1000),
            queue_status="sent",
        )
        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "statuses": [
                                    {
                                        "id": "wamid.status",
                                        "status": "delivered",
                                        "timestamp": str(int(time.time())),
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }
        resp = self.client.post(
            "/webhook/mensajes",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        mensaje = Mensaje.objects.get(wa_message_id="wamid.status")
        assert mensaje.delivery_status == "delivered"

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_cliente_nuevo_recibe_bienvenida(self, mocked_send, mocked_read):
        resp = self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        assert resp.status_code == 200
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        assert Cliente.objects.count() == 1
        assert Sesion.objects.count() == 1
        assert Mensaje.objects.filter(direccion="in").count() == 1
        assert Mensaje.objects.filter(direccion="out").count() == 1
        assert mocked_send.called
        enviado_texto = mocked_send.call_args[0][1]
        assert "Bienvenida" in enviado_texto
        assert "Opcion 1" in enviado_texto
        assert "Volver al menu principal" not in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_seleccionar_opcion_respuesta(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("1", numero="5491112345678", tipo="text")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Respuesta 1" in enviado_texto
        assert enviado_texto.count("Volver al menu principal") == 1
        assert enviado_texto.count("Volver atras") == 1

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_interactive_reply_id_short_title(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload_interactive(reply_id="1", reply_title="Servicios")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Respuesta 1" in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_seleccionar_opcion_submenu(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("2")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("A")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Contenido con nav" in enviado_texto
        assert enviado_texto.count("Volver al menu principal") == 1
        assert enviado_texto.count("Volver atras") == 1

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_volver_atras_regresa_menu_anterior(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("2")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("#")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Menu" in enviado_texto
        assert "Opcion 1" in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_no_texto_devuelve_menu(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola", tipo="image")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "puedo leer mensajes de texto" in enviado_texto.lower()
        assert "Menu" in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_sesion_expirada_reinicia_menu(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        sesion = Sesion.objects.first()
        sesion.ultimo_acceso_ms = int((time.time() - 10) * 1000)
        sesion.save(update_fields=["ultimo_acceso_ms"])

        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("1")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Sesion expirada" in enviado_texto
        assert "Menu" in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_opcion_invalida(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("99")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Opcion no valida" in enviado_texto
        assert "Volver al" in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_help_command(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("*")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "COMANDOS" in enviado_texto

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_menu_principal_comando(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("2")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("0")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "Menu" in enviado_texto
        assert "Opcion 1" in enviado_texto

    def test_formato_numero_549(self):
        mensajes, _ = views._extraer_eventos_whatsapp(self._payload("hola"))
        assert mensajes[0]["phone_number"].startswith("+54")

    @patch("app.services.cliente_whatsapp.ClienteWhatsApp.marcar_como_leido", return_value=True)
    @patch(
        "app.services.cliente_whatsapp.ClienteWhatsApp.enviar_mensaje_con_resultado",
        return_value={"ok": True, "message_id": "wamid.out"},
    )
    def test_texto_libre_devuelve_menu(self, mocked_send, mocked_read):
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("hola")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        self.client.post(
            "/webhook/mensajes",
            data=json.dumps(self._payload("Quiero informacion de piletas")),
            content_type="application/json",
        )
        procesar_inbound_pendientes(limit=10)
        procesar_outbound_pendientes(limit=10)
        enviado_texto = mocked_send.call_args[0][1]
        assert "elegi una opcion del menu" in enviado_texto.lower()
