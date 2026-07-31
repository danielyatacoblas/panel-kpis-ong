# 03 · Dashboard de KPIs — todas las métricas del programa en un solo lugar

[![tests](https://img.shields.io/badge/tests-26%20passed-brightgreen)](tests/)
[![deploy](https://img.shields.io/badge/deploy-Vercel%20(gratis)-black)](#-publicarlo-gratis-en-vercel-5-minutos)
[![sin dependencias](https://img.shields.io/badge/frontend-sin%20dependencias-informational)](public/index.html)
[![licencia](https://img.shields.io/badge/licencia-MIT-blue)](LICENSE)

**Valida del aviso:** construir y mantener un dashboard de KPIs · automatizar la
actualización desde CRM, redes, email y formularios · **proponer mejoras a qué
métricas se miden y cómo se visualizan**.

---

## 🎬 Qué es

Un dashboard **estático y gratuito** que centraliza los KPIs del programa:
captación, email, redes, web y gestión educativa. Sin servidor, sin base de
datos, sin librerías externas — se despliega en Vercel y cuesta S/ 0.

```
CRM · Mailchimp · Meta/LinkedIn/TikTok · GA4 · Formularios
        │  (Apps Script + n8n, cada madrugada)
        ▼
   warehouse/  (histórico diario, una tabla por fuente)
        │  python scripts/construir_dashboard.py
        ▼
   public/datos.json  ──►  dashboard estático  ──►  Vercel (URL pública)
```

### Cómo se ve

Vista clara y oscura, ambas con la paleta validada para daltonismo
(el validador de contraste/CVD pasa en los dos modos):

| Bloque | Forma elegida | Por qué |
| --- | --- | --- |
| Leads generados | **Hero** (número grande + variación + sparkline) | Es el número que lidera el tablero |
| 9 indicadores | **Fila de tiles** con delta vs período anterior | Un vistazo, sin gráficos innecesarios |
| Captación diaria | Línea + media móvil de 7 días | La estacionalidad semanal tapa la tendencia |
| Canales | Barras con rampa secuencial | Comparar magnitudes, no identidades |
| Alcance por red | 4 líneas categóricas + leyenda + etiquetas directas | Las series *son* el tema |
| Apertura de email | Columnas + línea de promedio | Detecta campañas bajo el promedio |
| Asistencia por taller | Barras | Comparación simple entre 4 talleres |

---

## ⚡ Probarlo en 1 minuto

```bash
pip install pytest
python scripts/generar_warehouse.py       # 90 días de data ficticia
python scripts/construir_dashboard.py     # calcula KPIs → public/datos.json
python -m pytest tests/ -v                # 26 tests

# ver el dashboard
cd public && python -m http.server 8899   # → http://localhost:8899
```

Salida real de `construir_dashboard.py`:

```
KPIs calculados:
  Leads generados                226.00        ▲ +3.7 % vs período anterior
  Tasa de conversión              33.63%       ▲ +1.8 % vs período anterior
  Días a primera respuesta         0.92 días   ▼ -4.2 % vs período anterior
  Apertura de email               27.81%       ▼ -12.2 % vs período anterior
  Clics de email                   4.11%       ▼ -24.0 % vs período anterior
  Alcance en redes            79,478.00        ▲ +5.5 % vs período anterior
  Interacción en redes             5.61%       ▲ +7.9 % vs período anterior
  Sesiones web                 7,622.00        ▲ +6.7 % vs período anterior
  Asistencia a talleres           68.61%       ▼ -1.5 % vs período anterior
  Beneficiarios activos           58.00        ▼ -15.9 % vs período anterior
```

> La data ficticia esconde a propósito **un problema detectable**: la apertura
> de email cae en las últimas semanas. El dashboard lo detecta solo y muestra
> una alerta con la recomendación. Un tablero que solo dice "todo bien" no
> sirve para nada.

---

## 🚀 Publicarlo gratis en Vercel (5 minutos)

1. Sube este proyecto a GitHub (ver la guía del repo raíz).
2. Entra a <https://vercel.com> → **Add New… → Project** → conecta tu GitHub.
3. Elige el repositorio. Vercel detecta `vercel.json`; confirma:
   - **Framework Preset:** `Other`
   - **Build Command:** *(vacío)*
   - **Output Directory:** `public`
4. **Deploy**. En ~30 s tendrás una URL tipo
   `https://club-stem-kpis.vercel.app` — pública, con HTTPS y CDN, gratis.

**Actualización automática sin servidor:** el workflow
`.github/workflows/actualizar-datos.yml` regenera `datos.json` cada madrugada
con GitHub Actions (gratis), corre los tests y hace push; Vercel redespliega
solo al detectar el commit. Cero infraestructura que mantener.

---

## 🔌 Conectar datos reales (cuando reemplaces la data ficticia)

1. Crea una Google Sheet con las pestañas `leads`, `email`, `redes`, `web`,
   `educacion`, `log` (mismas columnas que los CSV de `warehouse/`).
2. Pega `apps_script/extractores.gs` en Extensiones → Apps Script.
3. Guarda las credenciales en **Propiedades del script** (nunca en el código):
   `MAILCHIMP_API_KEY`, `MAILCHIMP_LIST_ID`, `META_TOKEN`, `IG_USER_ID`,
   `GA4_PROPERTY_ID`.
4. Activadores → `ejecutarTodo` → diario 03:00.
5. En `construir_dashboard.py`, cambia la lectura de CSV por la descarga de la
   hoja (`https://docs.google.com/spreadsheets/d/<ID>/gviz/tq?tqx=out:csv`).

El extractor ya trae lo que se olvida siempre: **cada fuente corre aislada**
(si Mailchimp falla, GA4 igual se extrae), **deduplicación por fecha**,
**log de cada corrida** y **alerta por correo si algo falla**.

---

## 📊 Decisiones de visualización (y por qué)

- **Un solo eje por gráfico.** Nunca dos escalas Y: es la forma más común de
  mentir con un gráfico. Dos medidas distintas → dos gráficos.
- **Paleta validada, no elegida a ojo.** Se corrió el validador de
  contraste/daltonismo sobre los 4 colores en modo claro y oscuro. Los 4 pasan
  las separaciones CVD; por eso las líneas llevan además **etiqueta directa**.
- **El color nunca es el único canal.** Leyenda + etiquetas directas + botón
  **"Ver tablas"** que muestra todos los datos en tablas accesibles.
- **Etiquetas selectivas.** Valor en la punta de cada barra y al final de cada
  línea; nunca un número sobre cada punto.
- **Ejes con números redondos** y grilla de 1px recesiva: el dato es lo único
  que debe destacar.
- **Media móvil visible junto al dato crudo**, para que nadie confunda
  suavizado con realidad.
- **Modo oscuro seleccionado**, no invertido: los colores oscuros son otros
  pasos de la misma rampa, validados contra el fondo oscuro.

---

## 📁 Estructura

```
03_dashboard_kpis/
├── public/
│   ├── index.html          # dashboard completo (HTML+CSS+JS, sin dependencias)
│   └── datos.json          # generado; lo consume el front
├── src/kpis.py             # todas las fórmulas (una función por métrica)
├── scripts/
│   ├── generar_warehouse.py    # 90 días de data ficticia reproducible
│   └── construir_dashboard.py  # warehouse → KPIs → datos.json
├── warehouse/              # histórico por fuente (CSV)
├── apps_script/extractores.gs  # extracción real programada
├── tests/test_kpis.py      # 26 tests, incluido el contrato con el front
├── .github/workflows/      # actualización automática gratis
├── vercel.json             # configuración de despliegue
└── METRICAS.md             # diccionario de métricas
```

---

## 🧪 Qué está probado

| Área | Tests |
| --- | --- |
| Fórmulas | Cada KPI con valores calculados a mano |
| Bordes | Denominador cero → 0, listas vacías, sin infinitos |
| Ventanas | El período anterior **no se solapa** y es del mismo largo |
| Series | Días sin datos se rellenan con 0; media móvil correcta |
| Multi-serie | Todas las series comparten el mismo eje temporal *(este test encontró un bug real durante el desarrollo)* |
| Contrato | `datos.json` tiene exactamente la forma que el dashboard espera |

---

## 📌 Estado

✅ **Funcional, probado y listo para desplegar.** 26 tests en verde, dashboard
verificado visualmente en modo claro y oscuro, data ficticia de 90 días
incluida y actualización automática configurada.
