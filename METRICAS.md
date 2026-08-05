# Diccionario de métricas — Club STEM

> Sin esto, dos personas miran el mismo número y entienden cosas distintas.
> Cada métrica declara **qué mide, cómo se calcula, de dónde sale y quién
> responde por ella**.

Las métricas marcadas con  son **propuestas** que el aviso no listaba pero que
cambian decisiones. Están implementadas y probadas.

---

## 1. Captación

| Métrica | Definición | Fórmula | Fuente | Responsable |
| --- | --- | --- | --- | --- |
| **Leads generados** | Personas que dejaron sus datos en el período | `count(leads)` | CRM (Sheets) | Comunicaciones |
| **Tasa de conversión** | % de leads que terminan inscritos en un programa | `convertidos / leads × 100` | CRM | Comunicaciones |
| **Conversión por canal** | Lo mismo, abierto por canal de origen | `convertidos[canal] / leads[canal] × 100` | CRM | Comunicaciones |
| **Días a primera respuesta** | Promedio de días hasta el primer contacto del equipo | `promedio(dias_a_primera_respuesta)` | CRM | Coordinación |

**Por qué importan las dos últimas.** El volumen por canal dice *cuánta* gente
llega; la conversión dice *cuál sirve*. Un canal puede traer el 30 % de los
leads y convertir el 20 %, mientras otro trae el 7 % y convierte el 67 %: sin
cruzar ambas se invierte en el canal equivocado. Y el tiempo de respuesta es el
factor más controlable de la conversión — bajarlo no cuesta pauta, cuesta
proceso.

**Dirección:** en "días a primera respuesta", **menos es mejor** (el dashboard
lo marca en verde cuando baja).

---

## 2. Email marketing

| Métrica | Definición | Fórmula | Fuente | Responsable |
| --- | --- | --- | --- | --- |
| **Tasa de apertura** | % de correos entregados que se abrieron | `aperturas / enviados × 100` | Mailchimp API | Comunicaciones |
| **Tasa de clics (CTR)** | % de correos enviados con al menos un clic | `clics / enviados × 100` | Mailchimp API | Comunicaciones |
| **Crecimiento de lista** | Suscriptores netos ganados en el período | `suscriptores(fin) − suscriptores(inicio)` | Mailchimp API | Comunicaciones |

**Decisión de cálculo:** el CTR se mide **sobre enviados**, no sobre aperturas.
El CTR sobre aperturas (CTOR) sube artificialmente cuando la apertura baja, y
eso hace que una campaña mala parezca buena. Sobre enviados, las campañas son
comparables entre sí.

> La apertura depende de píxeles de seguimiento y está inflada/deflactada
> por Apple Mail Privacy Protection. Sirve para comparar campañas entre sí, no
> como número absoluto. **El clic es la métrica confiable.**

---

## 3. Redes sociales

| Métrica | Definición | Fórmula | Fuente | Responsable |
| --- | --- | --- | --- | --- |
| **Alcance** | Personas únicas que vieron contenido | `suma(alcance)` | Meta / LinkedIn / TikTok API | Comunicaciones |
| **Tasa de interacción** | % del alcance que interactuó | `interacciones / alcance × 100` | APIs de redes | Comunicaciones |
| **Alcance por red** | Alcance abierto por plataforma | `suma(alcance) agrupado por red` | APIs de redes | Comunicaciones |

**Ojo con el alcance.** Es la métrica más fácil de inflar y la que menos dice
por sí sola: un pico de alcance sin interacción ni leads no es un logro. Por eso
el dashboard la muestra junto a la tasa de interacción y no como titular.

---

## 4. Sitio web

| Métrica | Definición | Fórmula | Fuente | Responsable |
| --- | --- | --- | --- | --- |
| **Sesiones** | Visitas al sitio en el período | `suma(sesiones)` | GA4 vía Apps Script | Web |
| **Usuarios** | Personas únicas estimadas | `suma(usuarios)` | GA4 | Web |
| **Tasa de rebote** | % de sesiones sin interacción | promedio ponderado | GA4 | Web |

---

## 5. Gestión educativa

| Métrica | Definición | Fórmula | Fuente | Responsable |
| --- | --- | --- | --- | --- |
| **Beneficiarios activos** | Asistentes en la última jornada registrada | `suma(asistentes) de la última fecha` | Formularios de asistencia | Coordinación |
| **Tasa de asistencia** | % de inscritos que efectivamente asisten | `asistentes / inscritos × 100` | Formularios | Coordinación |
| **Asistencia por taller** | Lo mismo, abierto por taller | `asistentes[taller] / inscritos[taller] × 100` | Formularios | Coordinación |

**Por qué la asistencia y no solo los inscritos.** Inscribirse es gratis;
asistir cuesta tiempo, transporte y ganas. La asistencia real mide la calidad
del programa y detecta talleres con problemas (horario, sede, contenido) que el
número de inscritos esconde.

---

## 6. Reglas transversales

- **Ventanas comparables.** Toda variación compara los últimos N días contra los
  N inmediatamente anteriores, sin solapamiento. Comparar 30 días contra "el mes
  pasado" (que puede tener 28 o 31) produce variaciones falsas.
- **Denominador cero = 0, nunca error.** Si no hubo envíos, la tasa es 0 y el
  dashboard no se rompe.
- **Días sin datos valen 0, no se saltan.** En las series diarias los huecos se
  rellenan; una línea que "salta" días miente sobre la tendencia.
- **Media móvil de 7 días** en las series diarias: la estacionalidad semanal
  (fines de semana bajos) tapa la tendencia real si se grafica el dato crudo.
- **Histórico diario.** El warehouse guarda el valor de cada día, no solo el
  actual: sin histórico no hay tendencia ni comparación posible.

---

## 7. Qué NO medimos (y por qué)

| No medimos | Motivo |
| --- | --- |
| Seguidores como KPI principal | Métrica de vanidad: no se correlaciona con inscripciones |
| Impresiones | Infladas por el algoritmo; el alcance de personas únicas es más honesto |
| Tiempo en página como éxito | Puede significar interés o confusión; sin contexto no decide nada |
| Datos personales de menores | Solo agregados. Ningún KPI requiere identificar a un participante |

---

## 8. Frecuencia de actualización

| Fuente | Frecuencia | Mecanismo |
| --- | --- | --- |
| CRM (leads) | Tiempo real | Webhook de n8n al llegar el lead |
| Email | Diaria 03:00 | Apps Script → Mailchimp API |
| Redes | Diaria 03:00 | Apps Script → Meta/LinkedIn/TikTok API |
| Web | Diaria 03:00 | Apps Script → GA4 Data API |
| Educación | Al cerrar cada jornada | Formulario de asistencia |

Si una fuente falla dos días seguidos, el extractor envía alerta al responsable
(ver `apps_script/extractores.gs`). El dashboard muestra la fecha de última
actualización para que nadie tome decisiones con datos viejos sin saberlo.

---

## 9. Asistente de análisis

El asistente no es un modelo de lenguaje: es un conjunto de reglas que leen los
KPIs y desgloses del período activo. Vive en `public/index.html`, función
`hallazgos()`, y sus tests están en `tests/probar_asistente.mjs`.

### Las reglas

| Regla | Se dispara cuando | Nivel |
| --- | --- | --- |
| Canal líder que no convierte | El canal con más volumen queda por debajo de la mediana de conversión | Decidir |
| Canal líder que sí convierte | El canal con más volumen queda por encima de la mediana | Sostener |
| Oportunidad desaprovechada | El canal con mejor conversión aporta menos del 25 % del volumen | Vigilar |
| Caída de apertura de email | Las últimas 3 campañas promedian menos del 90 % del promedio del período | Decidir |
| Mayor retroceso | El KPI con peor variación, respetando si "mejor" es arriba o abajo | Decidir si cae más del 10 %, si no Vigilar |
| Mayor avance | El KPI con mejor variación | Sostener |
| Asistencia baja | La asistencia real cae por debajo del 75 % | Vigilar |

Las cifras de cada texto salen del dato, nunca están escritas a mano: si la
asistencia sube, el titular deja de decir "4 de cada 10".

### Por qué determinista y no un modelo

Las afirmaciones de este panel mueven presupuesto. Un modelo redacta mejor pero
puede afirmar lo que los datos no dicen, y sobre un tablero eso es peor que no
decir nada. Las reglas se pueden auditar una por una, se pueden probar con
datos conocidos, y el mismo período da siempre el mismo texto.

Además, así el tablero desplegado no necesita credenciales ni tiene coste por
consulta: sigue siendo un archivo estático.

### Conectarlo a un modelo real

Toda la generación de texto está en una función:

```js
function responder(pregunta) { ... }   // devuelve {texto, lista}
```

Para usar un modelo, se reemplaza por una llamada a la API pasándole
`vista()` (los KPIs y desgloses del período) y se devuelve la misma forma. El
resto del tablero no se entera.

Lo razonable en producción es lo híbrido: que las reglas sigan decidiendo
**qué** es relevante —eso es auditable— y que el modelo solo redacte el
resumen. Así nunca aparece un número que no venga del warehouse.
