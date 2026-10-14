# ADR-046: El tope de un mensaje del chat sube a 20 000 caracteres

- **Estado:** Aceptado · **Fecha:** 2026-10-12 · **Modifica:** ADR-043 (punto 3, tope del chat)

## Contexto
- ADR-043 puso 8000 caracteres por mensaje para que un mensaje de 1 MB no fuera entero a
  la moderación y al modelo.
- El usuario pidió 20 000: 8000 se queda corto para pegar un texto o un fragmento de
  código largo y pedir que se explique.

## Decisión
- `MAX_CHAT_MESSAGE_CHARS = 20_000` en `/chats/{id}/messages` y `/stream`; más es **422**.
- El frontend sube su contador al mismo número.

## Por qué es seguro
- **Historial:** `recent_history` recorta cada mensaje anterior a 1500 caracteres y el
  total a 24 000, así que solo el turno actual viaja entero al modelo.
- **Coste:** 20 000 caracteres son unos 5000–6000 tokens de entrada para un turno; cabe
  holgado en el contexto de gpt-4o y en la moderación.
- **Abuso:** se mantienen el rate limit del chat y el resto de ADR-043. Lo que el tope
  evitaba (mensajes de megas) sigue cerrado.

## Verificado
- `tests/api/test_chats_api.py`: 20 001 caracteres → 422; 20 000 se aceptan y se guardan.
