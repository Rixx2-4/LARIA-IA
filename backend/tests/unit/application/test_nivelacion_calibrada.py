"""Nivelación calibrada (ADR-031): rúbrica de dificultad, sin repetir rondas, avanzada con modelo fuerte.

Medido con un evaluador (gpt-4o) sobre 5 temas: antes, las preguntas "difíciles"
tenían nivel cognitivo medio 1.75/3 y un tercio de la ronda avanzada repetía la
base. Después: 2.48/3 y 10 %.
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.quiz_service import QuizService, repeated_questions
from src.domain.catalog.prerequisite_seeds import build_seeded_graph
from src.domain.services.diagnostic_planner import PlacementRound, plan_diagnostic
from src.domain.services.tutor_policy import TutorPolicy
from src.domain.value_objects.question import Quiz, QuizQuestion
from src.infrastructure.persistence.in_memory_quiz_repo import InMemoryQuizRepository


def _q(texto, dif="easy"):
    return QuizQuestion(text=texto, options={"A": "a", "B": "b", "C": "c", "D": "d"},
                        correct_answer="A", difficulty=dif, concept_tags=("fraccion",))


def _ronda(prefijo, difs):
    """Ítems con el reparto real del plan (ADR-045): si no, el servicio los rechaza."""
    return [_q(f"{prefijo} {i}", d) for i, d in enumerate(difs)]


BASE = ("easy",) * 4 + ("medium",) * 2
AVANZADA = ("medium",) * 3 + ("hard",) * 5


def test_el_prompt_define_que_es_cada_dificultad_y_pide_una_sola_correcta():
    s = TutorPolicy().generate_diagnostic(plan_diagnostic("fracciones", build_seeded_graph())).system

    assert "hard = resolver un problema de VARIOS pasos" in s
    assert "nunca se responde recordando un dato" in s
    assert "Una sola opción correcta" in s and "errores típicos" in s


def test_el_prompt_lista_las_preguntas_que_no_debe_repetir():
    plan = plan_diagnostic("fracciones", build_seeded_graph(), PlacementRound.AVANZADA)

    s = TutorPolicy().generate_diagnostic(plan, avoid=("¿Qué es una fracción?",)).system

    assert "NO repitas" in s and "¿Qué es una fracción?" in s


def test_repetidas_detecta_reformulaciones_casi_literales():
    previas = ("¿Qué es una fracción propia?",)

    assert repeated_questions([_q("¿Qué es una fracción propia?"), _q("Calcula 3/4 + 1/8")], previas) == 1


class AnalistaFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.llamadas = []

    async def generate_diagnostic(self, plan, *, model=None, avoid=()):
        self.llamadas.append(SimpleNamespace(model=model, avoid=avoid, round=plan.round))
        return Quiz(questions=self.respuestas.pop(0))


def _servicio(analista, repo):
    return QuizService(
        document_repository=AsyncMock(), quiz_repository=repo, attempt_repository=AsyncMock(),
        interaction_repository=AsyncMock(), ia_analyst=analista, strong_model="gpt-4o",
    )


@pytest.mark.asyncio
async def test_la_ronda_avanzada_recibe_las_preguntas_previas_y_usa_el_modelo_fuerte():
    repo = InMemoryQuizRepository()
    base = _ronda("¿Pregunta base sobre fracciones?", BASE)
    avanzada = _ronda("Problema avanzado con varios pasos", AVANZADA)
    analista = AnalistaFalso([base, avanzada])
    servicio, user = _servicio(analista, repo), uuid4()
    grafo = build_seeded_graph()

    await servicio._quiz_por_tema(plan_diagnostic("fracciones", grafo, PlacementRound.BASE), user)
    await servicio._quiz_por_tema(plan_diagnostic("fracciones", grafo, PlacementRound.AVANZADA), user)

    primera, segunda = analista.llamadas
    assert primera.model is None and primera.avoid == ()
    assert segunda.model == "gpt-4o"
    assert set(segunda.avoid) == {q.text for q in base}


@pytest.mark.asyncio
async def test_si_repite_se_genera_otra_vez_y_se_queda_la_que_menos_repite():
    repo = InMemoryQuizRepository()
    base = _ronda("¿Pregunta base?", BASE)
    repetida = [_q("¿Pregunta base? 0", "medium")] + _ronda("Nueva con pasos", AVANZADA[1:])
    limpia = _ronda("Distinta con varios pasos", AVANZADA)
    analista = AnalistaFalso([base, repetida, limpia])
    servicio, user = _servicio(analista, repo), uuid4()
    grafo = build_seeded_graph()

    await servicio._quiz_por_tema(plan_diagnostic("fracciones", grafo, PlacementRound.BASE), user)
    quiz = await servicio._quiz_por_tema(plan_diagnostic("fracciones", grafo, PlacementRound.AVANZADA), user)

    assert len(analista.llamadas) == 3
    assert all(q.text.startswith("Distinta") for q in quiz.questions)


def test_el_reparto_del_plan_se_cumple_y_lo_que_sobra_se_descarta():
    """ADR-045: en producción una ronda avanzada (3 medias + 5 difíciles) llegó con
    10 ítems y 3 fáciles, que inflaban el aprobado."""
    from src.domain.services.diagnostic_planner import fit_to_plan

    plan = plan_diagnostic("fracciones", build_seeded_graph(), PlacementRound.AVANZADA)
    generadas = _ronda("Fácil", ("easy",) * 3) + _ronda("Media", ("medium",) * 4) + _ronda("Dura", ("hard",) * 5)
    elegidas, cumple = fit_to_plan(generadas, plan)
    assert cumple and len(elegidas) == 8
    assert [q.difficulty for q in elegidas].count("medium") == 3
    assert not any(q.text.startswith("Fácil") for q in elegidas)

    corta, cumple = fit_to_plan(_ronda("Media", ("medium",) * 3) + _ronda("Dura", ("hard",) * 2), plan)
    assert not cumple and len(corta) == 5


@pytest.mark.asyncio
async def test_si_el_reparto_no_cuadra_se_regenera_una_vez():
    repo = InMemoryQuizRepository()
    mala = _ronda("Fácil", ("easy",) * 3) + _ronda("Media", ("medium",) * 3) + _ronda("Dura", ("hard",) * 2)
    buena = _ronda("Buena", AVANZADA)
    analista = AnalistaFalso([mala, buena])
    servicio, user = _servicio(analista, repo), uuid4()

    quiz = await servicio._quiz_por_tema(plan_diagnostic("fracciones", build_seeded_graph(), PlacementRound.AVANZADA), user)

    assert len(analista.llamadas) == 2
    assert len(quiz.questions) == 8 and all(q.text.startswith("Buena") for q in quiz.questions)
