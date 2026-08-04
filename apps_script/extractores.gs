/**
 * Club STEM — Extractores de KPIs con Google Apps Script
 * ------------------------------------------------------
 * Corre programado (Activadores → cada día a las 03:00) y deja en la hoja
 * "warehouse" una fila por día y por fuente. El dashboard lee de ahí.
 *
 * INSTALACIÓN
 * 1. Crea una Google Sheet con las pestañas: leads, email, redes, web, educacion, log
 * 2. Extensiones → Apps Script → pega este archivo
 * 3. Configuración del proyecto → Propiedades del script: agrega las claves
 * (MAILCHIMP_API_KEY, MAILCHIMP_LIST_ID, META_TOKEN, GA4_PROPERTY_ID…)
 * 4. Activadores → Agregar activador → ejecutarTodo → Basado en tiempo → Diario 03:00
 *
 * NUNCA se escriben credenciales en el código: van en Propiedades del script.
 */

const HOJA_LOG = 'log';

/** Punto de entrada del activador diario. */
function ejecutarTodo() {
  const inicio = new Date();
  const resultados = [];

  // Cada extractor se ejecuta aislado: si una API falla, las demás continúan.
  resultados.push(ejecutarSeguro('email', extraerEmail));
  resultados.push(ejecutarSeguro('redes', extraerRedes));
  resultados.push(ejecutarSeguro('web', extraerWeb));

  const fallidos = resultados.filter(r => !r.ok);
  registrarLog(inicio, resultados);

  // Si algo falló, avisar (no fallar en silencio).
  if (fallidos.length) {
    notificar(' Extracción de KPIs con errores: ' +
              fallidos.map(f => f.fuente + ' (' + f.error + ')').join(', '));
  }
}

/** Envuelve un extractor para que un error no tumbe al resto. */
function ejecutarSeguro(fuente, fn) {
  try {
    const filas = fn();
    return { fuente: fuente, ok: true, filas: filas, error: '' };
  } catch (e) {
    return { fuente: fuente, ok: false, filas: 0, error: String(e).slice(0, 200) };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Extractores por fuente
// ─────────────────────────────────────────────────────────────────────────────

/** Mailchimp: campañas enviadas en las últimas 24 h. */
function extraerEmail() {
  const props = PropertiesService.getScriptProperties();
  const apiKey = props.getProperty('MAILCHIMP_API_KEY');
  const listId = props.getProperty('MAILCHIMP_LIST_ID');
  if (!apiKey) throw new Error('falta MAILCHIMP_API_KEY en Propiedades del script');

  const dc = apiKey.split('-')[1];               // el data center va en la key
  const desde = new Date(Date.now() - 24 * 3600 * 1000).toISOString();
  const url = 'https://' + dc + '.api.mailchimp.com/3.0/campaigns' +
              '?status=sent&since_send_time=' + encodeURIComponent(desde) +
              '&list_id=' + listId + '&count=50';

  const resp = UrlFetchApp.fetch(url, {
    headers: { Authorization: 'Basic ' + Utilities.base64Encode('anystring:' + apiKey) },
    muteHttpExceptions: true,
  });
  if (resp.getResponseCode() !== 200) {
    throw new Error('Mailchimp HTTP ' + resp.getResponseCode());
  }

  const campanas = JSON.parse(resp.getContentText()).campaigns || [];
  const filas = campanas.map(function (c) {
    const r = c.report_summary || {};
    return [
      c.send_time.slice(0, 10),                  // fecha
      c.settings.title || c.id,                  // campana
      (c.recipients && c.recipients.recipient_count) || 0,  // suscriptores
      (r.emails_sent != null ? r.emails_sent : 0),          // enviados
      r.opens || 0,                              // aperturas
      r.clicks || 0,                             // clics
      r.unsubscribed || 0,                       // bajas
    ];
  });
  escribirFilas('email', filas);
  return filas.length;
}

/** Meta Graph API: alcance e interacciones de ayer por red. */
function extraerRedes() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('META_TOKEN');
  const igId = props.getProperty('IG_USER_ID');
  if (!token) throw new Error('falta META_TOKEN en Propiedades del script');

  const ayer = Utilities.formatDate(
    new Date(Date.now() - 24 * 3600 * 1000), 'America/Lima', 'yyyy-MM-dd');

  const url = 'https://graph.facebook.com/v20.0/' + igId + '/insights' +
              '?metric=reach,accounts_engaged&period=day&access_token=' + token;
  const resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true });
  if (resp.getResponseCode() !== 200) {
    throw new Error('Meta HTTP ' + resp.getResponseCode());
  }

  const data = JSON.parse(resp.getContentText()).data || [];
  const valor = function (nombre) {
    const m = data.filter(function (d) { return d.name === nombre; })[0];
    return (m && m.values && m.values[0] && m.values[0].value) || 0;
  };

  const filas = [[ayer, 'instagram', 1, valor('reach'), valor('accounts_engaged'), 0]];
  escribirFilas('redes', filas);
  return filas.length;
}

/** GA4 Data API: sesiones y usuarios de ayer. */
function extraerWeb() {
  const props = PropertiesService.getScriptProperties();
  const propertyId = props.getProperty('GA4_PROPERTY_ID');
  if (!propertyId) throw new Error('falta GA4_PROPERTY_ID en Propiedades del script');

  // Requiere habilitar el servicio avanzado "Google Analytics Data" en Apps Script.
  const informe = AnalyticsData.Properties.runReport({
    dateRanges: [{ startDate: 'yesterday', endDate: 'yesterday' }],
    dimensions: [{ name: 'date' }],
    metrics: [{ name: 'sessions' }, { name: 'totalUsers' },
              { name: 'screenPageViews' }, { name: 'bounceRate' }],
  }, 'properties/' + propertyId);

  const filas = (informe.rows || []).map(function (r) {
    const d = r.dimensionValues[0].value;        // yyyymmdd
    const fecha = d.slice(0, 4) + '-' + d.slice(4, 6) + '-' + d.slice(6, 8);
    const m = r.metricValues.map(function (v) { return Number(v.value) || 0; });
    return [fecha, m[0], m[1], m[2], 0, Number(m[3].toFixed(3))];
  });
  escribirFilas('web', filas);
  return filas.length;
}

// ─────────────────────────────────────────────────────────────────────────────
// Utilidades de hoja
// ─────────────────────────────────────────────────────────────────────────────

/** Agrega filas al final de una pestaña, evitando duplicar la misma fecha. */
function escribirFilas(pestana, filas) {
  if (!filas.length) return;
  const hoja = SpreadsheetApp.getActive().getSheetByName(pestana);
  if (!hoja) throw new Error('no existe la pestaña "' + pestana + '"');

  // clave = fecha + segunda columna (campaña / red), para no duplicar
  const existentes = {};
  const datos = hoja.getDataRange().getValues();
  for (let i = 1; i < datos.length; i++) {
    existentes[String(datos[i][0]) + '|' + String(datos[i][1])] = true;
  }
  const nuevas = filas.filter(function (f) {
    return !existentes[String(f[0]) + '|' + String(f[1])];
  });
  if (!nuevas.length) return;

  hoja.getRange(hoja.getLastRow() + 1, 1, nuevas.length, nuevas[0].length)
      .setValues(nuevas);
}

/** Deja constancia de cada corrida: qué fuente, cuántas filas, si falló. */
function registrarLog(inicio, resultados) {
  const hoja = SpreadsheetApp.getActive().getSheetByName(HOJA_LOG);
  if (!hoja) return;
  const dur = ((Date.now() - inicio.getTime()) / 1000).toFixed(1);
  const filas = resultados.map(function (r) {
    return [new Date(), r.fuente, r.ok ? 'ok' : 'error', r.filas, r.error, dur + ' s'];
  });
  hoja.getRange(hoja.getLastRow() + 1, 1, filas.length, filas[0].length)
      .setValues(filas);
}

/** Aviso al equipo (correo del propietario; se puede cambiar por Telegram). */
function notificar(mensaje) {
  MailApp.sendEmail({
    to: Session.getEffectiveUser().getEmail(),
    subject: 'Club STEM · Extracción de KPIs',
    body: mensaje + '\n\nRevisa la pestaña "log" de la hoja para el detalle.',
  });
}

/** Para probar a mano desde el editor sin esperar al activador. */
function probarExtraccion() {
  const r = ejecutarSeguro('email', extraerEmail);
  Logger.log(JSON.stringify(r, null, 2));
}
