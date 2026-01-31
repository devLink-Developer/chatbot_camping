# Analisis de menus y propuesta de mensajes interactivos (WhatsApp)

Fuente: `colecciones_v1/chatbot.menus.json` y `colecciones_v1/chatbot.respuestas.json`.
Objetivo: reducir opciones invalidas, acortar mensajes, evitar duplicados de "volver" y mejorar la UX sin IA.

## 1) Estado actual (resumen)
- **Menu principal (id 0)**: 12 opciones + "volver al menu principal".
- **Menus con submenu**: 2, 3, 4, 5, 7, 10, 11, 12.
- **Menus directos** (respuesta directa): 1, 6, 8, 9.
- **Respuestas** incluyen lineas de navegacion dentro del texto:
  - "Volver al menu principal"
  - "Volver atras"
  Esto genera **repeticiones** cuando se envia el menu y luego la respuesta.

## 2) Propuesta general
1) **Menu principal** -> usar **interactive list** (lista) en vez de texto.
2) **Submenus con mas de 3 opciones** -> **interactive list**.
3) **Submenus con 2 o 3 opciones** -> **reply buttons** (botones).
4) **Respuestas directas** -> texto + botones de navegacion (menu principal / atras).
5) **Eliminar las lineas "volver" dentro del texto** cuando se use interactive,
   y construir la navegacion como botones/listas.

## 3) Propuesta por menu (interactive.type)

| Menu ID | Titulo (actual)                              | Opciones | Tipo sugerido | Notas |
|--------:|----------------------------------------------|:--------:|:-------------:|------|
| 0       | Menu principal                                | 12       | list          | Dividir en secciones para no saturar |
| 1       | Que servicios tiene el parque                 | 1        | text + buttons| Respuesta directa |
| 2       | Que esta prohibido                            | 4        | list          | Opciones A-D |
| 3       | Informacion para pasar el dia                 | 3        | buttons       | A/B/C |
| 4       | Informacion de camping diario                 | 3        | buttons       | A/B/C |
| 5       | Informacion de piscinas                       | 3        | buttons       | A/B/C |
| 6       | Informacion sobre canchas                     | 1        | text + buttons| Respuesta directa |
| 7       | Club de casas rodantes                        | 2        | buttons       | A/B |
| 8       | Grupos y contingentes                         | 1        | text + buttons| Respuesta directa |
| 9       | Asociate al ACA                               | 1        | text + buttons| Respuesta directa |
| 10      | Como llegar                                   | 5        | list          | A-E |
| 11      | Otros centros turisticos                      | 2        | buttons       | A/B |
| 12      | Tramites de socios oficina local              | 2        | buttons       | A/B |

## 4) Detalle de opciones y mapping sugerido
La idea es mantener compatibilidad con lo actual (numeros/letras)
y **mapear** los IDs de los botones/listas a los mismos codigos:

### Menu 0 (principal) -> list
**Rows sugeridas (id -> accion existente):**
- `m0_1` -> "1"
- `m0_2` -> "2"
- `m0_3` -> "3"
- `m0_4` -> "4"
- `m0_5` -> "5"
- `m0_6` -> "6"
- `m0_7` -> "7"
- `m0_8` -> "8"
- `m0_9` -> "9"
- `m0_10` -> "10"
- `m0_11` -> "11"
- `m0_12` -> "12"
- `m0_0` -> "0" (volver al menu principal)

Secciones sugeridas:
- **Servicios**: 1, 3, 4, 5, 6, 7
- **Informacion**: 2, 8, 9, 10
- **Otros**: 11, 12

### Menu 2 (prohibido) -> list
**Rows:**
- `m2_a` -> "2A"
- `m2_b` -> "2B"
- `m2_c` -> "2C"
- `m2_d` -> "2D"
- `m2_0` -> "0"

### Menu 3 (pasar el dia) -> buttons
**Buttons:**
- `m3_a` -> "3A"
- `m3_b` -> "3B"
- `m3_c` -> "3C"

### Menu 4 (camping diario) -> buttons
**Buttons:**
- `m4_a` -> "4A"
- `m4_b` -> "4B"
- `m4_c` -> "4C"

### Menu 5 (piscinas) -> buttons
**Buttons:**
- `m5_a` -> "5A"
- `m5_b` -> "5B"
- `m5_c` -> "5C"

### Menu 7 (casas rodantes) -> buttons
**Buttons:**
- `m7_a` -> "7A"
- `m7_b` -> "7B"

### Menu 10 (como llegar) -> list
**Rows:**
- `m10_a` -> "10A"
- `m10_b` -> "10B"
- `m10_c` -> "10C"
- `m10_d` -> "10D"
- `m10_e` -> "10E"
- `m10_0` -> "0"

### Menu 11 (otros centros) -> buttons
**Buttons:**
- `m11_a` -> "11A"
- `m11_b` -> "11B"

### Menu 12 (tramites socios) -> buttons
**Buttons:**
- `m12_a` -> "12A"
- `m12_b` -> "12B"

## 5) Respuestas (texto) y navegacion
Actualmente las respuestas incluyen:
- "Volver al menu principal"
- "Volver atras"

**Recomendacion**:
- Quitar esas lineas del texto base.
- Luego **agregar navegacion como botones**:
  - Boton: `menu_principal`
  - Boton: `volver_atras` (solo si el flujo tiene padre)

Esto evita el problema observado de repeticion y "opcion invalida".

## 6) Compatibilidad con texto libre
Aunque usemos interactive, mantener compatibilidad con:
- numeros: `1..12`, `0`
- letras: `A..E`
- comandos: `#` para volver atras

Si llega texto libre, se procesa igual que hoy.

## 7) Cambios tecnicos sugeridos (alto nivel)
- Agregar en `ClienteWhatsApp`:
  - `enviar_interactive_buttons(...)`
  - `enviar_interactive_list(...)`
- Agregar un **builder** que devuelva el payload de menu segun `menu_id`.
- Control por setting: `WHATSAPP_INTERACTIVE_ENABLED=true`
- Si no hay soporte, fallback a texto actual.

## 8) Prioridad de implementacion
1) Menu principal -> list
2) Menus 2 y 10 -> list
3) Menus 3/4/5/7/11/12 -> buttons
4) Limpiar texto de respuestas y mover navegacion a botones

---
Si queres, puedo convertir este analisis en tareas concretas de codigo
y dejarlo implementado con los payloads exactos.
