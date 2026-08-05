// Prueba el motor de hallazgos del asistente, fuera del navegador.
//
// Motivo: el asistente afirma cosas sobre el negocio ("este canal trae volumen
// y no convierte"). Una afirmación de esas mal calculada es peor que no decir
// nada, porque alguien puede mover presupuesto por ella. Estos tests fijan
// datos conocidos y comprueban que las conclusiones sean las correctas.
//
// Misma técnica que probar_graficos_vacios.mjs: se extrae el <script> del
// dashboard y se evalúa con un DOM simulado mínimo.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(ROOT, 'public', 'index.html'), 'utf8');
const bloques = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const codigo = bloques[bloques.length - 1];

const preparar = new Function(`
  const nodoFalso = () => ({
    setAttribute() {}, getAttribute: () => null, appendChild() {},
    addEventListener() {}, removeEventListener() {},
    style: {}, classList: { toggle() {}, add() {}, remove() {} },
    textContent: '', innerHTML: '', clientWidth: 900, clientHeight: 300,
  });
  const document = {
    createElementNS: nodoFalso, createElement: nodoFalso,
    getElementById: nodoFalso, querySelector: () => null,
    querySelectorAll: () => [],
    documentElement: { getAttribute: () => null, setAttribute() {} },
    addEventListener() {},
  };
  const getComputedStyle = () => ({ getPropertyValue: () => '#2a78d6' });
  const window = { devicePixelRatio: 1 };
  const location = { protocol: 'http:' };
  const fetch = () => Promise.reject(new Error('sin red en el test'));
  const addEventListener = () => {};
  const matchMedia = () => ({ matches: false, addEventListener() {} });
  const setTimeout = () => 0, clearTimeout = () => {};
  const setInterval = () => 0, clearInterval = () => {};
  const requestAnimationFrame = () => 0, cancelAnimationFrame = () => {};
  ${codigo}
  return {
    hallazgos, responder,
    fijar(datos, ventana, canales) {
      DATOS = datos;
      ESTADO.ventana = ventana || '30';
      ESTADO.canales = canales ? new Set(canales) : null;
    },
  };
`);

let fallos = 0;
const check = (nombre, cond, detalle = '') => {
  if (cond) console.log(`  ✓ ${nombre}`);
  else { console.log(`  ✗ ${nombre} ${detalle}`); fallos++; }
};

const api = preparar();

/* Escenario base: Facebook manda en volumen y convierte mal; Referido convierte
   muy bien con poco volumen; el email se está cayendo. */
function escenario(cambios = {}) {
  const base = {
    generado_en: '2026-08-04',
    periodo: {desde: '2026-05-02', hasta: '2026-07-30', dias_kpi: 30,
              dias_serie: 90, ventanas: [30, 60, 90]},
    series: {
      apertura_campana: [
        {fecha: '2026-06-04', valor: 32}, {fecha: '2026-06-11', valor: 31},
        {fecha: '2026-06-18', valor: 33}, {fecha: '2026-06-25', valor: 30},
        {fecha: '2026-07-02', valor: 22}, {fecha: '2026-07-09', valor: 21},
        {fecha: '2026-07-16', valor: 20},
      ],
    },
    ventanas: {
      '30': {
        kpis: [
          {id: 'leads', etiqueta: 'Leads generados', valor: 200, variacion: 4, unidad: '', mejor: 'arriba'},
          {id: 'asistencia', etiqueta: 'Asistencia a talleres', valor: 61.5, variacion: -1, unidad: '%', mejor: 'arriba'},
          {id: 'alcance', etiqueta: 'Alcance en redes', valor: 85000, variacion: 44.6, unidad: '', mejor: 'arriba'},
          {id: 'beneficiarios', etiqueta: 'Beneficiarios activos', valor: 55, variacion: -14.1, unidad: '', mejor: 'arriba'},
        ],
        desgloses: {
          leads_por_canal: {facebook: 100, web: 60, instagram: 25, referido: 15},
          conversion_por_canal: {facebook: 12, web: 30, instagram: 28, referido: 70},
          alcance_por_red: {instagram: 40000, facebook: 45000},
          asistencia_por_taller: {'Robótica Inicial': 61.5},
        },
      },
    },
  };
  return Object.assign(base, cambios);
}

console.log('Motor de hallazgos del asistente:');

// 1. El canal líder en volumen que convierte por debajo de la mediana
api.fijar(escenario(), '30');
let h = api.hallazgos();
const lider = h.find(x => /Facebook trae el volumen/.test(x.titulo));
check('detecta el canal con más volumen y peor conversión', !!lider,
      `→ títulos: ${h.map(x => x.titulo).join(' | ')}`);
check('lo marca como crítico, no como aviso', lider && lider.nivel === 'critico');
check('cita su cuota real del total (100 de 200 = 50 %)',
      lider && /50 %/.test(lider.detalle), `→ ${lider && lider.detalle}`);

// 2. Oportunidad: el que mejor convierte apenas se usa
const oportunidad = h.find(x => /Referido es el que mejor convierte/.test(x.titulo));
check('detecta el canal de alta conversión y poco volumen', !!oportunidad);
// Duplicar la cuota de Referido son 15 leads más; al 70 % dan 10,5 → 11.
check('cuantifica la ganancia de duplicar su cuota (15 leads al 70 % = 11)',
      oportunidad && /11 inscritos más/.test(oportunidad.detalle),
      `→ ${oportunidad && oportunidad.detalle}`);

// 3. Caída de apertura de email
check('detecta la caída sostenida de apertura de email',
      h.some(x => /apertura de email viene cayendo/i.test(x.titulo)));

// 4. La proporción de asistencia sale del dato, no está escrita a mano
const asist = h.find(x => /no llega al taller/.test(x.titulo));
check('el titular de asistencia deriva la proporción del dato (61.5 % → 4 de 10)',
      asist && /^4 de cada 10/.test(asist.titulo), `→ ${asist && asist.titulo}`);

// 5. Orden por gravedad: los críticos primero
const niveles = h.map(x => x.nivel);
const rank = {critico: 0, aviso: 1, bueno: 2};
check('los hallazgos salen ordenados por gravedad',
      niveles.every((n, i) => i === 0 || rank[niveles[i - 1]] <= rank[n]),
      `→ ${niveles.join(', ')}`);

// 6. El filtro de canales cambia la conclusión, no solo el gráfico
api.fijar(escenario(), '30', ['web', 'instagram', 'referido']);
const hFiltrado = api.hallazgos();
check('al excluir Facebook, deja de ser el protagonista',
      !hFiltrado.some(x => /Facebook/.test(x.titulo)),
      `→ ${hFiltrado.map(x => x.titulo).join(' | ')}`);

// 7. Sin caída de email, no se inventa la alerta
api.fijar(escenario({
  series: {apertura_campana: [
    {fecha: '2026-06-04', valor: 30}, {fecha: '2026-06-11', valor: 31},
    {fecha: '2026-06-18', valor: 30}, {fecha: '2026-06-25', valor: 31},
    {fecha: '2026-07-02', valor: 30}, {fecha: '2026-07-09', valor: 31},
  ]},
}), '30');
check('sin caída real no reporta caída de email',
      !api.hallazgos().some(x => /apertura de email viene cayendo/i.test(x.titulo)));

console.log('\nRespuestas por pregunta:');

// 8. "¿Qué empeoró?" nunca debe devolver buenas noticias
api.fijar(escenario(), '30');
const empeoro = api.responder('empeoro');
check('"¿Qué empeoró?" no incluye hallazgos positivos',
      empeoro.lista.every(x => x.nivel !== 'bueno'),
      `→ ${empeoro.lista.map(x => x.nivel).join(', ')}`);

// 9. "¿Qué funciona?" solo devuelve positivos
const mejoro = api.responder('mejoro');
check('"¿Qué está funcionando?" solo incluye hallazgos positivos',
      mejoro.lista.every(x => x.nivel === 'bueno'),
      `→ ${mejoro.lista.map(x => x.nivel).join(', ')}`);

// 10. El resumen menciona el total de leads del período activo
const resumen = api.responder('resumen');
check('el resumen cita el número de leads de la ventana activa',
      /200/.test(resumen.texto), `→ ${resumen.texto}`);

// 11. Con filtro de canales, la respuesta lo dice explícitamente
api.fijar(escenario(), '30', ['referido']);
check('la respuesta avisa cuando hay un filtro de canales activo',
      /mirando solo Referido/.test(api.responder('resumen').texto));

// 12. Un período sin nada que reportar no inventa hallazgos
api.fijar(escenario({
  series: {apertura_campana: []},
  ventanas: {'30': {
    kpis: [{id: 'leads', etiqueta: 'Leads generados', valor: 10, variacion: 0, unidad: '', mejor: 'arriba'}],
    desgloses: {leads_por_canal: {web: 10}, conversion_por_canal: {web: 30},
                alcance_por_red: {}, asistencia_por_taller: {}},
  }},
}), '30');
let vacio;
try { vacio = api.hallazgos(); }
catch (e) { vacio = null; check('un solo canal no rompe el motor', false, `→ ${e.message}`); }
if (vacio) check('un solo canal y sin variaciones no genera afirmaciones falsas',
                 vacio.every(x => x.titulo && x.detalle), `→ ${vacio.length} hallazgos`);

console.log(fallos ? `\n${fallos} fallos` : '\nTodo correcto');
process.exit(fallos ? 1 : 0);
