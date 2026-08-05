// Prueba los gráficos del dashboard con datos vacíos, fuera del navegador.
//
// Motivo: una fuente sin datos (una red que el Club aún no usa, una API caída)
// hacía que el gráfico multi-serie lanzara excepción y rompiera el resto del
// tablero. Este test evita que vuelva a pasar.
//
// No usa jsdom ni ninguna dependencia: con datos vacíos las funciones salen
// por la guarda inicial, así que basta un contenedor simulado mínimo.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const html = readFileSync(join(ROOT, 'public', 'index.html'), 'utf8');

const bloques = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
if (!bloques.length) {
  console.error('no se encontró el bloque <script> del dashboard');
  process.exit(1);
}
const codigo = bloques[bloques.length - 1];

// Contenedor simulado: solo lo que tocan las guardas de estado vacío.
function contenedorFalso() {
  return {
    innerHTML: '',
    clientWidth: 900,
    clientHeight: 300,
    querySelector: () => null,
    appendChild() {},
  };
}

// Se expone lo necesario para poder invocar las funciones desde el test.
// getElementById devuelve un elemento simulado (nunca null): el código del
// dashboard engancha listeners a los botones al cargar, y con null lanzaría
// antes de que podamos probar nada.
const preparar = new Function(`
  const nodoFalso = () => ({
    setAttribute() {}, getAttribute: () => null, appendChild() {},
    addEventListener() {}, removeEventListener() {},
    style: {}, classList: { toggle() {}, add() {}, remove() {} },
    textContent: '', innerHTML: '', clientWidth: 900, clientHeight: 300,
    getContext: () => ({ setTransform() {}, clearRect() {} }),
  });
  const document = {
    createElementNS: nodoFalso,
    createElement: nodoFalso,
    getElementById: nodoFalso,
    querySelector: () => null,
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
  const requestAnimationFrame = () => 0, cancelAnimationFrame = () => {};
  ${codigo}
  return { lineChart, barChart, columnChart, sparkline, escala };
`);

let fallos = 0;
const check = (nombre, cond, detalle = '') => {
  if (cond) { console.log(`  ✓ ${nombre}`); }
  else { console.log(`  ✗ ${nombre} ${detalle}`); fallos++; }
};

let api;
try {
  api = preparar();
} catch (e) {
  console.error('no se pudo cargar el código del dashboard:', e.message);
  process.exit(1);
}

console.log('Gráficos con datos vacíos (no deben lanzar excepción):');

// 1. Multi-línea sin ninguna serie — el caso que rompía el tablero
try {
  const c = contenedorFalso();
  api.lineChart(c, { series: [] });
  check('lineChart sin series muestra estado vacío',
        /Sin datos/.test(c.innerHTML), `innerHTML="${c.innerHTML.slice(0, 60)}"`);
} catch (e) {
  check('lineChart sin series no lanza excepción', false, `→ ${e.message}`);
}

// 2. Series presentes pero todas sin puntos
try {
  const c = contenedorFalso();
  api.lineChart(c, { series: [{ nombre: 'Instagram', color: '--s1', datos: [] }] });
  check('lineChart con series vacías muestra estado vacío',
        /Sin datos/.test(c.innerHTML));
} catch (e) {
  check('lineChart con series vacías no lanza excepción', false, `→ ${e.message}`);
}

// 3. Barras sin datos
try {
  const c = contenedorFalso();
  api.barChart(c, { datos: [] });
  check('barChart sin datos muestra estado vacío', /Sin datos/.test(c.innerHTML));
} catch (e) {
  check('barChart sin datos no lanza excepción', false, `→ ${e.message}`);
}

// 4. Columnas sin campañas
try {
  const c = contenedorFalso();
  api.columnChart(c, { datos: [] });
  check('columnChart sin datos muestra estado vacío',
        /Aún no hay campañas|Sin datos/.test(c.innerHTML));
} catch (e) {
  check('columnChart sin datos no lanza excepción', false, `→ ${e.message}`);
}

// 5. Sparkline sin puntos
try {
  const c = contenedorFalso();
  api.sparkline(c, []);
  check('sparkline sin datos no dibuja nada', c.innerHTML === '');
} catch (e) {
  check('sparkline sin datos no lanza excepción', false, `→ ${e.message}`);
}

// 6. La escala del eje debe dar números redondos y nunca NaN
console.log('\nEscala de los ejes:');
for (const [entrada, esperado] of [
  [10.4, 5],        // 0 / 5 / 10 / 15 / 20
  [1, 0.25],        // 0 / 0.25 / 0.5 / 0.75 / 1
  [79478, 20000],   // 0 / 20K / 40K / 60K / 80K
  [0, 0.25],        // serie toda en cero: eje 0–1, no valores infinitesimales
  [-5, 0.25],       // valor imposible: tampoco debe romper
]) {
  const e = api.escala(entrada, 4);
  const ok = Number.isFinite(e.max) && Number.isFinite(e.paso) && e.max > 0
             && Math.abs(e.paso - esperado) < 1e-9;
  check(`escala(${entrada}) → paso ${e.paso}, max ${e.max}`, ok,
        `esperaba paso ${esperado}`);
}

console.log(fallos === 0
  ? '\n✓ todos los gráficos manejan datos vacíos sin romperse'
  : `\n✗ ${fallos} fallos`);
process.exit(fallos ? 1 : 0);
