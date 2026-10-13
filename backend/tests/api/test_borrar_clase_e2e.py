"""Borrar una clase quita la ruta, no lo aprendido.

La ruta es el plan de estudio; el dominio de cada concepto y el nivel del tema son
evidencia sobre el estudiante (los escribe el projector, invariante 1) y no se borran
con ella. Por eso, si vuelve a crear la clase del mismo tema, no repite la nivelación.
"""
import asyncio
from uuid import UUID

from tests.api.test_clase_e2e import (
    _auth,
    _comprobar,
    _correctas,
    _leccion,
    _nivelarse,
    _ruta,
    entorno,  # noqa: F401  (fixture)
)


def test_borrar_una_clase_quita_la_ruta_pero_conserva_lo_aprendido(entorno):  # noqa: F811
    c, _ = entorno
    h = _auth(c)
    yo = UUID(c.get("/api/v1/users/me", headers=h).json()["id"])
    perfiles = __import__("src.interfaces.api.dependencies", fromlist=["x"]).get_profile_repo()

    _nivelarse(c, h, "python", bien=False)
    ruta = _ruta(c, h, "python")
    paso = _leccion(c, h, ruta["id"])
    _comprobar(c, h, ruta["id"], paso["check"], _correctas(paso["check"]))
    antes = dict(asyncio.run(perfiles.find_by_student(yo)).mastery_by_concept)

    assert c.delete(f"/api/v1/learning/paths/{ruta['id']}", headers=h).status_code == 204

    assert c.get("/api/v1/learning/paths", headers=h).json()["paths"] == []
    assert c.get(f"/api/v1/learning/paths/{ruta['id']}", headers=h).status_code == 404
    assert c.post(f"/api/v1/learning/paths/{ruta['id']}/lesson", headers=h).status_code == 404
    assert c.delete(f"/api/v1/learning/paths/{ruta['id']}", headers=h).status_code == 404
    assert antes and dict(asyncio.run(perfiles.find_by_student(yo)).mastery_by_concept) == antes

    # Volver a crearla no pide otra nivelación: el nivel del tema sigue guardado.
    otra = _ruta(c, h, "python")
    assert otra["id"] != ruta["id"]
