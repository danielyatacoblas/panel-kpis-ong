#!/usr/bin/env python3
"""Genera el "warehouse" ficticio: 90 días de datos de las 5 fuentes del Club.

    python scripts/generar_warehouse.py

Simula lo que en producción llega por Apps Script / n8n desde:
  CRM (leads) · Mailchimp (email) · Meta+LinkedIn+TikTok (redes) ·
  GA4 (web) · formularios de asistencia (gestión educativa)

La data tiene patrones realistas a propósito para que el dashboard cuente
una historia: estacionalidad semanal, tendencia de crecimiento, picos por
campaña y una caída de la tasa de apertura en la última semana (para que
haya algo que detectar).
"""
from __future__ import annotations

import csv
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "warehouse"

random.seed(2026)

DIAS = 90
HOY = date(2026, 7, 30)
INICIO = HOY - timedelta(days=DIAS - 1)

CANALES = ["web", "facebook", "instagram", "podium", "referido"]
SEGMENTOS = ["talleres", "voluntariado", "donacion", "general"]
REDES = ["instagram", "facebook", "linkedin", "tiktok"]
TALLERES = ["Robótica Inicial", "Programación con Scratch",
            "Ciencia en Casa", "Matemática Lúdica"]

# días con campaña (picos de tráfico y leads)
CAMPANAS = {INICIO + timedelta(days=d) for d in (12, 34, 56, 78)}


def _estacional(d: date) -> float:
    """Fin de semana baja, martes/miércoles alto."""
    return {0: 1.05, 1: 1.15, 2: 1.12, 3: 1.0, 4: 0.9, 5: 0.6, 6: 0.55}[d.weekday()]


def _tendencia(i: int) -> float:
    """Crecimiento suave del 35 % en los 90 días."""
    return 1 + 0.35 * (i / DIAS)


def _ruido(pct=0.18) -> float:
    return 1 + random.uniform(-pct, pct)


def generar_leads() -> list[dict]:
    filas = []
    lid = 0
    for i in range(DIAS):
        d = INICIO + timedelta(days=i)
        base = 6 * _estacional(d) * _tendencia(i) * _ruido()
        if d in CAMPANAS:
            base *= 2.6
        for _ in range(max(0, int(round(base)))):
            lid += 1
            canal = random.choices(CANALES, weights=[30, 22, 26, 14, 8])[0]
            segmento = random.choices(SEGMENTOS, weights=[52, 16, 10, 22])[0]
            # la conversión depende del canal y del segmento (realista)
            p = {"web": .30, "facebook": .22, "instagram": .25,
                 "podium": .38, "referido": .45}[canal]
            if segmento == "talleres":
                p += .12
            elif segmento == "general":
                p -= .10
            convertido = random.random() < max(0.05, p)
            filas.append({
                "fecha": d.isoformat(), "lead_id": f"L{lid:05d}",
                "canal": canal, "segmento": segmento,
                "convertido": int(convertido),
                "dias_a_primera_respuesta": random.choices(
                    [0, 1, 2, 3, 5], weights=[45, 28, 14, 8, 5])[0],
            })
    return filas


def generar_email() -> list[dict]:
    filas = []
    suscriptores = 1850
    envio = 0
    for i in range(DIAS):
        d = INICIO + timedelta(days=i)
        suscriptores += random.randint(2, 14)
        if d.weekday() != 3:        # newsletter los jueves
            continue
        envio += 1
        enviados = int(suscriptores * random.uniform(0.94, 0.99))
        # apertura ~32 % pero cae en las últimas 2 semanas (hay algo que detectar)
        tasa = 0.32 * _ruido(0.08)
        if i > DIAS - 15:
            tasa *= 0.72
        aperturas = int(enviados * tasa)
        clics = int(aperturas * random.uniform(0.12, 0.22))
        filas.append({
            "fecha": d.isoformat(), "campana": f"Newsletter #{envio:02d}",
            "suscriptores": suscriptores, "enviados": enviados,
            "aperturas": aperturas, "clics": clics,
            "bajas": random.randint(0, 6),
        })
    return filas


def generar_redes() -> list[dict]:
    filas = []
    seguidores = {"instagram": 4200, "facebook": 3100,
                  "linkedin": 890, "tiktok": 1500}
    for i in range(DIAS):
        d = INICIO + timedelta(days=i)
        for red in REDES:
            publico = random.random() < {"instagram": .8, "facebook": .7,
                                         "linkedin": .35, "tiktok": .5}[red]
            if not publico:
                continue
            base = {"instagram": 950, "facebook": 620,
                    "linkedin": 380, "tiktok": 1600}[red]
            alcance = int(base * _estacional(d) * _tendencia(i) * _ruido(0.35))
            if d in CAMPANAS:
                alcance = int(alcance * 2.2)
            inter = int(alcance * random.uniform(0.025, 0.085))
            seguidores[red] += max(0, int(inter * random.uniform(0.01, 0.05)))
            filas.append({
                "fecha": d.isoformat(), "red": red, "posts": 1,
                "alcance": alcance, "interacciones": inter,
                "seguidores": seguidores[red],
            })
    return filas


def generar_web() -> list[dict]:
    filas = []
    for i in range(DIAS):
        d = INICIO + timedelta(days=i)
        base = 210 * _estacional(d) * _tendencia(i) * _ruido(0.22)
        if d in CAMPANAS:
            base *= 2.4
        sesiones = int(base)
        filas.append({
            "fecha": d.isoformat(),
            "sesiones": sesiones,
            "usuarios": int(sesiones * random.uniform(0.72, 0.88)),
            "paginas_vistas": int(sesiones * random.uniform(1.9, 3.2)),
            "duracion_media_seg": int(random.uniform(65, 190)),
            "tasa_rebote": round(random.uniform(0.38, 0.62), 3),
        })
    return filas


def generar_educacion() -> list[dict]:
    """Sesiones de taller con inscritos y asistentes (retención real)."""
    filas = []
    for i in range(DIAS):
        d = INICIO + timedelta(days=i)
        if d.weekday() != 5:        # talleres los sábados
            continue
        for taller in TALLERES:
            inscritos = random.randint(18, 30)
            # la asistencia decae un poco a lo largo del ciclo (realista)
            tasa = random.uniform(0.68, 0.92) - 0.0012 * i
            filas.append({
                "fecha": d.isoformat(), "taller": taller,
                "inscritos": inscritos,
                "asistentes": max(5, int(inscritos * tasa)),
                "sede": random.choice(["Villa El Salvador", "Villa María"]),
            })
    return filas


def _escribir(nombre: str, filas: list[dict]):
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / nombre
    with p.open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        wr.writeheader()
        wr.writerows(filas)
    print(f"  ✓ {p.name:<22} {len(filas):>5} filas")


def main():
    print(f"Generando warehouse ficticio ({DIAS} días: "
          f"{INICIO.isoformat()} → {HOY.isoformat()})\n")
    _escribir("leads.csv", generar_leads())
    _escribir("email.csv", generar_email())
    _escribir("redes.csv", generar_redes())
    _escribir("web.csv", generar_web())
    _escribir("educacion.csv", generar_educacion())
    print(f"\n✓ warehouse/ listo. Ahora: python scripts/construir_dashboard.py")


if __name__ == "__main__":
    main()
