"""Tests de los KPIs.

Las métricas son el producto de este proyecto: si una fórmula está mal, el
equipo toma decisiones con números falsos. Por eso cada una tiene su test con
valores calculados a mano.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import kpis  # noqa: E402


# ── utilidades base ─────────────────────────────────────────────────────────

def test_tasa_calcula_porcentaje():
    assert kpis.tasa(25, 100) == 25.0
    assert kpis.tasa(1, 3) == 33.33


def test_tasa_no_explota_con_denominador_cero():
    assert kpis.tasa(5, 0) == 0.0


def test_variacion_entre_periodos():
    assert kpis.variacion(110, 100) == 10.0
    assert kpis.variacion(90, 100) == -10.0


def test_variacion_con_periodo_anterior_en_cero():
    assert kpis.variacion(50, 0) == 0.0, "no debe dar infinito ni romper"


def test_ventana_filtra_por_rango_inclusivo():
    filas = [{"fecha": "2026-07-01"}, {"fecha": "2026-07-15"},
             {"fecha": "2026-07-30"}, {"fecha": "2026-06-01"}]
    r = kpis.ventana(filas, date(2026, 7, 30), 30)
    assert len(r) == 3, "julio completo entra, junio no"


def test_periodo_anterior_no_se_solapa_con_el_actual():
    filas = [{"fecha": f"2026-07-{d:02d}"} for d in range(1, 31)]
    act = kpis.ventana(filas, date(2026, 7, 30), 10)
    ant = kpis.periodo_anterior(filas, date(2026, 7, 30), 10)
    fechas_act = {f["fecha"] for f in act}
    fechas_ant = {f["fecha"] for f in ant}
    assert not (fechas_act & fechas_ant), "las ventanas no deben solaparse"
    assert len(act) == len(ant) == 10, "deben ser del mismo largo"


# ── captación ───────────────────────────────────────────────────────────────

LEADS = [
    {"fecha": "2026-07-01", "canal": "web", "segmento": "talleres",
     "convertido": 1, "dias_a_primera_respuesta": 0},
    {"fecha": "2026-07-02", "canal": "web", "segmento": "general",
     "convertido": 0, "dias_a_primera_respuesta": 2},
    {"fecha": "2026-07-03", "canal": "podium", "segmento": "talleres",
     "convertido": 1, "dias_a_primera_respuesta": 1},
    {"fecha": "2026-07-04", "canal": "podium", "segmento": "donacion",
     "convertido": 1, "dias_a_primera_respuesta": 1},
]


def test_tasa_conversion():
    assert kpis.tasa_conversion(LEADS) == 75.0     # 3 de 4


def test_leads_por_canal_ordenado_desc():
    r = kpis.leads_por_canal(LEADS)
    assert r == {"web": 2, "podium": 2}
    assert list(r)[0] in ("web", "podium")


def test_conversion_por_canal():
    r = kpis.conversion_por_canal(LEADS)
    assert r["web"] == 50.0        # 1 de 2
    assert r["podium"] == 100.0    # 2 de 2


def test_tiempo_primera_respuesta_promedia():
    assert kpis.tiempo_primera_respuesta(LEADS) == 1.0   # (0+2+1+1)/4


def test_conversion_con_lista_vacia_no_rompe():
    assert kpis.tasa_conversion([]) == 0.0
    assert kpis.leads_por_canal([]) == {}


# ── email ───────────────────────────────────────────────────────────────────

EMAIL = [
    {"fecha": "2026-07-02", "campana": "N1", "suscriptores": 1000,
     "enviados": 1000, "aperturas": 300, "clics": 50, "bajas": 2},
    {"fecha": "2026-07-09", "campana": "N2", "suscriptores": 1050,
     "enviados": 1000, "aperturas": 200, "clics": 30, "bajas": 1},
]


def test_tasa_apertura_es_sobre_el_total_enviado():
    assert kpis.tasa_apertura(EMAIL) == 25.0     # 500 de 2000


def test_tasa_clics_se_calcula_sobre_enviados():
    """CTR sobre enviados (no sobre aperturas) para ser comparable."""
    assert kpis.tasa_clics(EMAIL) == 4.0         # 80 de 2000


def test_crecimiento_lista():
    assert kpis.crecimiento_lista(EMAIL) == 50


# ── redes ───────────────────────────────────────────────────────────────────

REDES = [
    {"fecha": "2026-07-01", "red": "instagram", "alcance": 1000, "interacciones": 50},
    {"fecha": "2026-07-01", "red": "tiktok", "alcance": 3000, "interacciones": 150},
    {"fecha": "2026-07-02", "red": "instagram", "alcance": 1000, "interacciones": 100},
]


def test_alcance_total_y_por_red():
    assert kpis.alcance_total(REDES) == 5000
    assert kpis.alcance_por_red(REDES) == {"tiktok": 3000, "instagram": 2000}


def test_tasa_interaccion():
    assert kpis.tasa_interaccion(REDES) == 6.0   # 300 de 5000


# ── educación ───────────────────────────────────────────────────────────────

EDU = [
    {"fecha": "2026-07-04", "taller": "Robótica", "inscritos": 20, "asistentes": 15},
    {"fecha": "2026-07-04", "taller": "Scratch", "inscritos": 20, "asistentes": 10},
    {"fecha": "2026-07-11", "taller": "Robótica", "inscritos": 20, "asistentes": 18},
]


def test_tasa_asistencia_global():
    assert kpis.tasa_asistencia(EDU) == 71.67    # 43 de 60


def test_asistencia_por_taller():
    r = kpis.asistencia_por_taller(EDU)
    assert r["Robótica"] == 82.5     # 33 de 40
    assert r["Scratch"] == 50.0      # 10 de 20


def test_beneficiarios_activos_usa_la_ultima_fecha():
    assert kpis.beneficiarios_activos(EDU) == 18


# ── series ──────────────────────────────────────────────────────────────────

def test_serie_diaria_cuenta_filas_sin_campo():
    filas = [{"fecha": "2026-07-01"}, {"fecha": "2026-07-01"},
             {"fecha": "2026-07-03"}]
    s = kpis.serie_diaria(filas)
    assert [p["valor"] for p in s] == [2, 0, 1], "el día sin datos debe ser 0"


def test_serie_diaria_rellena_dias_faltantes():
    filas = [{"fecha": "2026-07-01", "v": 5}, {"fecha": "2026-07-05", "v": 3}]
    s = kpis.serie_diaria(filas, "v")
    assert len(s) == 5, "debe rellenar del 1 al 5"
    assert [p["fecha"] for p in s][-1] == "2026-07-05"


def test_serie_por_categoria_separa_series():
    s = kpis.serie_por_categoria(REDES, "red", "alcance")
    assert set(s) == {"instagram", "tiktok"}
    assert len(s["instagram"]) == len(s["tiktok"]), "mismo eje temporal"


def test_media_movil_suaviza():
    serie = [{"fecha": f"2026-07-{d:02d}", "valor": v}
             for d, v in enumerate([0, 10, 0, 10, 0, 10, 0], start=1)]
    s = kpis.media_movil(serie, 7)
    assert s[-1]["valor"] == pytest.approx(30 / 7, abs=0.01)
    assert len(s) == len(serie)


# ── resumen completo ────────────────────────────────────────────────────────

def test_resumen_devuelve_todos_los_kpis_con_variacion():
    datos = {"leads": LEADS, "email": EMAIL, "redes": REDES,
             "web": [{"fecha": "2026-07-01", "sesiones": 100}], "educacion": EDU}
    r = kpis.resumen(datos, date(2026, 7, 30), 30)
    ids = {k["id"] for k in r["kpis"]}
    assert {"leads", "conversion", "apertura", "alcance", "asistencia"} <= ids
    for k in r["kpis"]:
        assert {"valor", "anterior", "variacion", "etiqueta", "mejor"} <= set(k)


def test_kpi_de_tiempo_de_respuesta_marca_que_menos_es_mejor():
    datos = {"leads": LEADS, "email": [], "redes": [], "web": [], "educacion": []}
    r = kpis.resumen(datos, date(2026, 7, 30), 30)
    resp = next(k for k in r["kpis"] if k["id"] == "respuesta")
    assert resp["mejor"] == "abajo", "bajar el tiempo de respuesta es bueno"


# ── contrato con el dashboard ───────────────────────────────────────────────

def test_datos_json_tiene_la_forma_que_espera_el_dashboard():
    """Si alguien cambia el JSON y rompe el front, este test avisa."""
    import json
    p = ROOT / "public" / "datos.json"
    if not p.exists():
        pytest.skip("corre antes: python scripts/construir_dashboard.py")
    d = json.loads(p.read_text(encoding="utf-8"))

    assert {"generado_en", "periodo", "kpis", "desgloses", "series", "fuentes"} <= set(d)
    assert {"desde", "hasta", "dias_kpi"} <= set(d["periodo"])
    assert any(k["id"] == "leads" for k in d["kpis"]), "el hero necesita el KPI 'leads'"

    for s in ("leads_dia", "leads_dia_suavizado", "alcance_por_red", "apertura_campana"):
        assert s in d["series"], f"falta la serie {s}"
    for g in ("leads_por_canal", "conversion_por_canal", "asistencia_por_taller"):
        assert g in d["desgloses"], f"falta el desglose {g}"

    # las series de redes deben tener el mismo largo (mismo eje temporal)
    largos = {len(v) for v in d["series"]["alcance_por_red"].values()}
    assert len(largos) == 1, "las series por red deben compartir el eje X"

    # cada punto de serie tiene fecha y valor
    for p_ in d["series"]["leads_dia"][:5]:
        assert {"fecha", "valor"} <= set(p_)
