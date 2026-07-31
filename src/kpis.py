"""Cálculo de KPIs del programa a partir del warehouse.

Cada función implementa UNA métrica del diccionario (`METRICAS.md`), con la
misma definición documentada allí. Todas reciben las filas ya leídas (listas
de dicts) para poder testearlas sin tocar disco.

Convención: todas las tasas se devuelven en **porcentaje** (0-100) redondeado
a 2 decimales, y las comparaciones de período usan ventanas del mismo largo
(últimos N días vs los N anteriores) para que la variación sea honesta.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta


# ── utilidades ──────────────────────────────────────────────────────────────

def _f(v, por_defecto=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return por_defecto


def _i(v, por_defecto=0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return por_defecto


def _fecha(s: str) -> date:
    return date.fromisoformat(str(s)[:10])


def tasa(numerador: float, denominador: float) -> float:
    """Porcentaje seguro: si el denominador es 0, devuelve 0 (no explota)."""
    if not denominador:
        return 0.0
    return round(100.0 * numerador / denominador, 2)


def variacion(actual: float, anterior: float) -> float:
    """Variación porcentual entre dos períodos. Si antes era 0, devuelve 0."""
    if not anterior:
        return 0.0
    return round(100.0 * (actual - anterior) / anterior, 1)


def ventana(filas: list[dict], hasta: date, dias: int,
            campo_fecha: str = "fecha") -> list[dict]:
    """Filas dentro de los `dias` que terminan en `hasta` (ambos inclusive)."""
    desde = hasta - timedelta(days=dias - 1)
    return [f for f in filas if desde <= _fecha(f[campo_fecha]) <= hasta]


def periodo_anterior(filas: list[dict], hasta: date, dias: int,
                     campo_fecha: str = "fecha") -> list[dict]:
    """La ventana inmediatamente anterior, del mismo largo (comparación justa)."""
    fin = hasta - timedelta(days=dias)
    return ventana(filas, fin, dias, campo_fecha)


# ── captación ───────────────────────────────────────────────────────────────

def total_leads(leads: list[dict]) -> int:
    return len(leads)


def tasa_conversion(leads: list[dict]) -> float:
    """% de leads que se convirtieron en participantes inscritos."""
    convertidos = sum(1 for l in leads if _i(l.get("convertido")))
    return tasa(convertidos, len(leads))


def leads_por_canal(leads: list[dict]) -> dict[str, int]:
    acc: dict[str, int] = defaultdict(int)
    for l in leads:
        acc[l.get("canal", "desconocido")] += 1
    return dict(sorted(acc.items(), key=lambda kv: -kv[1]))


def conversion_por_canal(leads: list[dict]) -> dict[str, float]:
    """% de conversión por canal: dice DÓNDE invertir, no solo cuánto llega."""
    tot: dict[str, int] = defaultdict(int)
    conv: dict[str, int] = defaultdict(int)
    for l in leads:
        c = l.get("canal", "desconocido")
        tot[c] += 1
        conv[c] += _i(l.get("convertido"))
    return {c: tasa(conv[c], tot[c]) for c in sorted(tot, key=lambda x: -tot[x])}


def tiempo_primera_respuesta(leads: list[dict]) -> float:
    """Promedio de días hasta el primer contacto (métrica propuesta)."""
    vals = [_f(l.get("dias_a_primera_respuesta")) for l in leads
            if l.get("dias_a_primera_respuesta") not in (None, "")]
    if not vals:
        return 0.0
    return round(sum(vals) / len(vals), 2)


# ── email ───────────────────────────────────────────────────────────────────

def tasa_apertura(email: list[dict]) -> float:
    enviados = sum(_i(e.get("enviados")) for e in email)
    aperturas = sum(_i(e.get("aperturas")) for e in email)
    return tasa(aperturas, enviados)


def tasa_clics(email: list[dict]) -> float:
    """CTR sobre enviados (no sobre aperturas): comparable entre campañas."""
    enviados = sum(_i(e.get("enviados")) for e in email)
    clics = sum(_i(e.get("clics")) for e in email)
    return tasa(clics, enviados)


def crecimiento_lista(email: list[dict]) -> int:
    """Suscriptores ganados netos en el período."""
    if not email:
        return 0
    ordenados = sorted(email, key=lambda e: _fecha(e["fecha"]))
    return _i(ordenados[-1].get("suscriptores")) - _i(ordenados[0].get("suscriptores"))


# ── redes ───────────────────────────────────────────────────────────────────

def alcance_total(redes: list[dict]) -> int:
    return sum(_i(r.get("alcance")) for r in redes)


def alcance_por_red(redes: list[dict]) -> dict[str, int]:
    acc: dict[str, int] = defaultdict(int)
    for r in redes:
        acc[r.get("red", "otra")] += _i(r.get("alcance"))
    return dict(sorted(acc.items(), key=lambda kv: -kv[1]))


def tasa_interaccion(redes: list[dict]) -> float:
    alcance = sum(_i(r.get("alcance")) for r in redes)
    inter = sum(_i(r.get("interacciones")) for r in redes)
    return tasa(inter, alcance)


# ── web ─────────────────────────────────────────────────────────────────────

def sesiones_totales(web: list[dict]) -> int:
    return sum(_i(w.get("sesiones")) for w in web)


# ── gestión educativa ───────────────────────────────────────────────────────

def tasa_asistencia(educacion: list[dict]) -> float:
    inscritos = sum(_i(e.get("inscritos")) for e in educacion)
    asistentes = sum(_i(e.get("asistentes")) for e in educacion)
    return tasa(asistentes, inscritos)


def beneficiarios_activos(educacion: list[dict]) -> int:
    """Asistentes en la última fecha con actividad registrada."""
    if not educacion:
        return 0
    ultima = max(_fecha(e["fecha"]) for e in educacion)
    return sum(_i(e.get("asistentes")) for e in educacion
               if _fecha(e["fecha"]) == ultima)


def asistencia_por_taller(educacion: list[dict]) -> dict[str, float]:
    ins: dict[str, int] = defaultdict(int)
    asi: dict[str, int] = defaultdict(int)
    for e in educacion:
        t = e.get("taller", "otro")
        ins[t] += _i(e.get("inscritos"))
        asi[t] += _i(e.get("asistentes"))
    return {t: tasa(asi[t], ins[t]) for t in sorted(ins)}


# ── series temporales (para los gráficos) ───────────────────────────────────

def serie_diaria(filas: list[dict], campo: str | None = None,
                 desde: date | None = None, hasta: date | None = None
                 ) -> list[dict]:
    """Agrupa por fecha sumando `campo` (o contando filas si campo es None).

    Rellena con 0 los días sin datos para que la línea no mienta con saltos.
    """
    acc: dict[date, float] = defaultdict(float)
    for f in filas:
        d = _fecha(f["fecha"])
        acc[d] += _f(f.get(campo), 0.0) if campo else 1.0
    if not acc:
        return []
    ini = desde or min(acc)
    fin = hasta or max(acc)
    salida = []
    d = ini
    while d <= fin:
        v = acc.get(d, 0.0)
        salida.append({"fecha": d.isoformat(),
                       "valor": round(v, 2) if v % 1 else int(v)})
        d += timedelta(days=1)
    return salida


def serie_por_categoria(filas: list[dict], categoria: str, campo: str,
                        desde: date | None = None, hasta: date | None = None
                        ) -> dict[str, list[dict]]:
    """Una serie diaria por cada valor de `categoria` (ej. una por red social).

    Todas las series comparten el MISMO eje temporal (el rango global de los
    datos), aunque una categoría no tenga registros en algún día. Sin esto las
    líneas de un gráfico multi-serie quedan desalineadas y el gráfico miente.
    """
    if not filas:
        return {}
    grupos: dict[str, list[dict]] = defaultdict(list)
    for f in filas:
        grupos[f.get(categoria, "otro")].append(f)
    fechas = [_fecha(f["fecha"]) for f in filas]
    ini = desde or min(fechas)
    fin = hasta or max(fechas)
    return {k: serie_diaria(v, campo, ini, fin)
            for k, v in sorted(grupos.items())}


def media_movil(serie: list[dict], ventana_dias: int = 7) -> list[dict]:
    """Suaviza una serie diaria (la estacionalidad semanal tapa la tendencia)."""
    vals = [_f(p["valor"]) for p in serie]
    salida = []
    for i, p in enumerate(serie):
        ini = max(0, i - ventana_dias + 1)
        trozo = vals[ini:i + 1]
        salida.append({"fecha": p["fecha"],
                       "valor": round(sum(trozo) / len(trozo), 2)})
    return salida


# ── resumen completo ────────────────────────────────────────────────────────

def resumen(datos: dict[str, list[dict]], hasta: date, dias: int = 30) -> dict:
    """Calcula todos los KPIs del período y su variación vs el período anterior.

    `datos` = {"leads": [...], "email": [...], "redes": [...],
               "web": [...], "educacion": [...]}
    """
    act = {k: ventana(v, hasta, dias) for k, v in datos.items()}
    ant = {k: periodo_anterior(v, hasta, dias) for k, v in datos.items()}

    def kpi(nombre, etiqueta, fn, fuente, unidad="", mejor="arriba"):
        a, b = fn(act[fuente]), fn(ant[fuente])
        return {"id": nombre, "etiqueta": etiqueta, "valor": a,
                "anterior": b, "variacion": variacion(a, b),
                "unidad": unidad, "mejor": mejor, "fuente": fuente}

    return {
        "periodo_dias": dias,
        "hasta": hasta.isoformat(),
        "kpis": [
            kpi("leads", "Leads generados", total_leads, "leads"),
            kpi("conversion", "Tasa de conversión", tasa_conversion, "leads", "%"),
            kpi("respuesta", "Días a primera respuesta", tiempo_primera_respuesta,
                "leads", " días", mejor="abajo"),
            kpi("apertura", "Apertura de email", tasa_apertura, "email", "%"),
            kpi("clics", "Clics de email", tasa_clics, "email", "%"),
            kpi("alcance", "Alcance en redes", alcance_total, "redes"),
            kpi("interaccion", "Interacción en redes", tasa_interaccion, "redes", "%"),
            kpi("sesiones", "Sesiones web", sesiones_totales, "web"),
            kpi("asistencia", "Asistencia a talleres", tasa_asistencia,
                "educacion", "%"),
            kpi("beneficiarios", "Beneficiarios activos", beneficiarios_activos,
                "educacion"),
        ],
        "desgloses": {
            "leads_por_canal": leads_por_canal(act["leads"]),
            "conversion_por_canal": conversion_por_canal(act["leads"]),
            "alcance_por_red": alcance_por_red(act["redes"]),
            "asistencia_por_taller": asistencia_por_taller(act["educacion"]),
        },
    }
