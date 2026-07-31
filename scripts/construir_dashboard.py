#!/usr/bin/env python3
"""Construye el JSON que consume el dashboard estático.

    python scripts/generar_warehouse.py      # primero la data
    python scripts/construir_dashboard.py    # luego el JSON

Genera `public/datos.json` con KPIs, series y desgloses ya calculados.
En producción este paso lo ejecuta n8n / GitHub Actions cada madrugada, y el
dashboard queda como sitio estático (desplegable gratis en Vercel).
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import kpis  # noqa: E402

WH = ROOT / "warehouse"
SALIDA = ROOT / "public" / "datos.json"
RESPALDO = ROOT / "public" / "datos.js"      # copia embebida para abrir sin servidor

FUENTES = ("leads", "email", "redes", "web", "educacion")
DIAS_KPI = 30        # ventana de los KPIs
DIAS_SERIE = 90      # ventana de los gráficos


def leer(nombre: str) -> list[dict]:
    p = WH / f"{nombre}.csv"
    if not p.exists():
        raise SystemExit(f"falta {p} — corre primero: python scripts/generar_warehouse.py")
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    datos = {n: leer(n) for n in FUENTES}
    hasta = max(date.fromisoformat(f["fecha"][:10])
                for fuente in datos.values() for f in fuente)
    desde = hasta - timedelta(days=DIAS_SERIE - 1)

    res = kpis.resumen(datos, hasta, DIAS_KPI)

    leads_dia = kpis.serie_diaria(datos["leads"], None, desde, hasta)
    web_dia = kpis.serie_diaria(datos["web"], "sesiones", desde, hasta)
    alcance_red = kpis.serie_por_categoria(datos["redes"], "red", "alcance",
                                           desde, hasta)

    # apertura por campaña (puntual, no diaria: el newsletter es semanal)
    email_ordenado = sorted(kpis.ventana(datos["email"], hasta, DIAS_SERIE),
                            key=lambda e: e["fecha"])
    # Se usan los helpers seguros de kpis: una celda vacía o no numérica en la
    # hoja no debe tumbar la construcción del tablero.
    apertura_campana = [{
        "fecha": e.get("fecha", ""), "campana": e.get("campana", "(sin nombre)"),
        "valor": kpis.tasa(kpis._i(e.get("aperturas")), kpis._i(e.get("enviados"))),
        "clics": kpis.tasa(kpis._i(e.get("clics")), kpis._i(e.get("enviados"))),
    } for e in email_ordenado]

    salida = {
        "generado_en": date.today().isoformat(),
        "periodo": {"desde": desde.isoformat(), "hasta": hasta.isoformat(),
                    "dias_kpi": DIAS_KPI, "dias_serie": DIAS_SERIE},
        "kpis": res["kpis"],
        "desgloses": res["desgloses"],
        "series": {
            "leads_dia": leads_dia,
            "leads_dia_suavizado": kpis.media_movil(leads_dia, 7),
            "web_dia": web_dia,
            "web_dia_suavizado": kpis.media_movil(web_dia, 7),
            "alcance_por_red": {k: kpis.media_movil(v, 7)
                                for k, v in alcance_red.items()},
            "apertura_campana": apertura_campana,
        },
        "fuentes": [
            {"nombre": "CRM (leads)", "archivo": "leads.csv",
             "filas": len(datos["leads"]), "origen": "Google Sheets vía n8n"},
            {"nombre": "Email marketing", "archivo": "email.csv",
             "filas": len(datos["email"]), "origen": "Mailchimp API"},
            {"nombre": "Redes sociales", "archivo": "redes.csv",
             "filas": len(datos["redes"]), "origen": "Meta / LinkedIn / TikTok API"},
            {"nombre": "Sitio web", "archivo": "web.csv",
             "filas": len(datos["web"]), "origen": "GA4 vía Apps Script"},
            {"nombre": "Gestión educativa", "archivo": "educacion.csv",
             "filas": len(datos["educacion"]), "origen": "Formularios de asistencia"},
        ],
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1),
                      encoding="utf-8")

    # Copia embebida como respaldo: permite abrir el dashboard con doble clic.
    # Con el protocolo file:// el navegador bloquea fetch() por CORS, así que
    # sin esto el tablero se vería roto para quien no levante un servidor.
    RESPALDO.write_text(
        "// Generado por scripts/construir_dashboard.py — no editar a mano.\n"
        "// Respaldo para abrir el dashboard sin servidor (file://).\n"
        "window.DATOS_EMBEBIDOS = "
        + json.dumps(salida, ensure_ascii=False, separators=(",", ":"))
        + ";\n", encoding="utf-8")

    kb = SALIDA.stat().st_size / 1024
    print(f"✓ {SALIDA.relative_to(ROOT)} ({kb:.0f} KB)")
    print(f"✓ {RESPALDO.relative_to(ROOT)} "
          f"({RESPALDO.stat().st_size/1024:.0f} KB — respaldo para file://)")
    print(f"  período KPI: últimos {DIAS_KPI} días hasta {hasta}")
    print(f"  series: {DIAS_SERIE} días\n")
    print("KPIs calculados:")
    for k in res["kpis"]:
        flecha = "▲" if k["variacion"] > 0 else ("▼" if k["variacion"] < 0 else "=")
        print(f"  {k['etiqueta']:<26} {k['valor']:>10,.2f}{k['unidad']:<7} "
              f"{flecha} {k['variacion']:+.1f} % vs período anterior")


if __name__ == "__main__":
    main()
