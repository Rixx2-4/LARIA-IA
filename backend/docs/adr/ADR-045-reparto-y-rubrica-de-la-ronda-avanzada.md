# ADR-045: La ronda avanzada cumple su reparto y sus "difíciles" exigen razonar

- **Estado:** Aceptado · **Fecha:** 2026-10-12 · **Amplía:** ADR-031 (nivelación calibrada)

## Contexto
- En producción, de 8 intentos de la ronda avanzada se aprobaron 6, tres de ellos con
  8/8 o casi.
- **Las "difíciles" eran preguntas de recordar:** "¿Qué es un pipeline en CI/CD?" o
  "¿Qué tipo de función es e^x?".
- **El modelo no respetaba el reparto y nadie lo comprobaba:** en "teléfonos y
  procesadores" la ronda avanzada (3 medias + 5 difíciles) llegó con preguntas fáciles,
  que inflaban el aprobado.
- **Medición del generador actual** (5 temas, gpt-4o, clasificadas por un evaluador):
  - de 24 "hard", 16 exigían varios pasos, 5 un paso y 3 eran de recordar;
  - 3 de 5 rondas traían más ítems de los pedidos, con fáciles incluidas.

## Decisión
- **`fit_to_plan` (dominio, puro)** toma de lo generado, por peldaño y en orden, como
  mucho los ítems que pide el plan, y descarta lo que no corresponde a ningún peldaño.
- **Si un peldaño queda corto, se regenera una vez** y se queda la versión que cumple o
  que más aporta. Si no queda nada, responde 502. Se aplica a nivelaciones, prácticas y
  pruebas de paso.
- **Rúbrica de "hard" reforzada:**
  - trae un caso concreto con datos, código o una situación que analizar;
  - la respuesta no está literal en el enunciado;
  - nunca empieza por «¿Qué es…?», «¿Qué significa…?» ni «¿Cuál es la definición…?»;
  - se piden exactamente los ítems de cada dificultad.

## Verificado
- **Con el modelo real, tras el cambio:** de 24 "hard", 0 eran de recordar (antes 3),
  14 de varios pasos y 10 de un paso.
- **Las fáciles que el modelo añade** (3 de 5 temas) las descarta `fit_to_plan`.
- **Tests:**
  - `test_el_reparto_del_plan_se_cumple_y_lo_que_sobra_se_descarta`;
  - `test_si_el_reparto_no_cuadra_se_regenera_una_vez`;
  - los dobles de `test_nivelacion_calibrada.py` ahora respetan el reparto real.

## Pendiente
- Todavía ~40 % de las "hard" se resuelven en un paso. Si la tasa de aprobado de la ronda
  avanzada sigue alta, el siguiente paso es un evaluador que reclasifique como "medium"
  las "hard" de un solo paso antes de servir la ronda. Cuesta una llamada más (~3 s) por
  ronda avanzada.
- Las preguntas que ya están en producción no cambian: el efecto se verá en las rondas
  nuevas.
