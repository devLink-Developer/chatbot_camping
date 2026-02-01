from django.urls import path

from app import views

urlpatterns = [
    path("", views.root),
    path("api/health", views.health_check),
    path("api/webhook", views.webhook),
    path("webhook/mensajes", views.webhook_mensajes),
    path("simulador", views.simulador),
    path("simulador/", views.simulador),
    path("api/simulador", views.simulador_api),
    path("api/simulador/", views.simulador_api),
    path("api/sesion/<str:phone_number>", views.obtener_sesion),
    path("api/resetear-sesion/<str:phone_number>", views.resetear_sesion),
]
