# ADR-044: Reintentar un quiz es practicar, no evidencia

- **Estado:** Aceptado · **Fecha:** 2026-10-12 · **Completa:** ADR-043

## Contexto
- La respuesta de un intento muestra la correcta de cada pregunta. Los quizzes de
  documento y de práctica se pueden reintentar a propósito, para practicar.
- Pero cada reintento llegaba al projector como una medición más. Reintentar hasta
  acertar subía el dominio de esos conceptos sin que el estudiante supiera más.
- Eso rompe la invariante 4: la evidencia se pesa por su calidad, y responder con las
  soluciones a la vista no mide nada.

## Decisión
- El projector, que es el único escritor del perfil (invariante 1), aplica como
  evidencia **solo el primer intento** de cada quiz. El orden se decide por
  `completed_at` y, si empatan, por el id.
- Un reintento:
  - **sigue permitido** y se califica igual;
  - queda en el historial de interacciones;
  - marca su evento como aplicado, por idempotencia;
  - **no mueve** el dominio, el nivel ni el perfil del documento.
- Las nivelaciones y pruebas de paso ya no admiten reintento (ADR-043, 409). Las
  comprobaciones de la clase tampoco (`answer_check`).

## Verificado
- `tests/api/test_prueba_de_paso_e2e.py::test_reintentar_un_quiz_de_practica_no_cuenta_como_evidencia`:
  el dominio tras un reintento perfecto es igual al del primer intento fallido.
- Sin este cambio, ese test falla.
