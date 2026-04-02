/**
 * mock-api.js — Servidor de prueba para el frontend Vue
 * Corre en puerto 8000, no necesita PostgreSQL ni Redis
 * Uso: node mock-api.js
 */

const http = require('http')

// ── Datos de prueba ──────────────────────────────────────────────────────────
const USERS = [
  { id: 1, username: 'admin',    nombre: 'Administrador',    email: 'admin@ridac.mx',    rol: { id:1, nombre:'admin' },      activo: true },
  { id: 2, username: 'juan',     nombre: 'Juan Pérez',       email: 'juan@ridac.mx',     rol: { id:2, nombre:'usuario' },    activo: true },
  { id: 3, username: 'maria',    nombre: 'María García',     email: 'maria@ridac.mx',    rol: { id:2, nombre:'usuario' },    activo: true },
  { id: 4, username: 'supervisor', nombre: 'Carlos López',  email: 'carlos@ridac.mx',   rol: { id:3, nombre:'supervisor' }, activo: true },
]

const CARPETAS = [
  { id: 1, nombre: 'Carpeta 001 — Homicidios 2024', descripcion: 'Expedientes de homicidio', total_tomos: 12, tomos_procesados: 10 },
  { id: 2, nombre: 'Carpeta 002 — Robo calificado', descripcion: 'Expedientes de robo', total_tomos: 8,  tomos_procesados: 8  },
  { id: 3, nombre: 'Carpeta 003 — Fraude fiscal',   descripcion: 'Expedientes fiscales',  total_tomos: 5,  tomos_procesados: 3  },
]

// Estado de análisis IA por carpeta (se puede mutar en runtime)
const ANALISIS_ESTADO = {
  1: {
    estado_analisis: 'completado', progreso: 100,
    estadisticas: { total_diligencias: 8, total_personas: 12, total_lugares: 5, total_fechas: 23, total_alertas_activas: 2, promedio_dias_entre_actuaciones: 15 },
    alertas_mp: [
      { tipo: 'Inactividad prolongada', descripcion: 'Sin actuaciones por más de 60 días consecutivos' },
      { tipo: 'Plazo constitucional', descripcion: 'Plazo constitucional próximo a vencer (5 días)' },
    ],
    diligencias: [
      { tipo_diligencia: 'Declaración Ministerial', fecha: '2024-03-15', mp_responsable: 'Lic. Carlos Mendoza Ruiz', numero_oficio: 'MP/2024/001', resumen: 'Declaración inicial del implicado Juan López Martínez ante el Ministerio Público sobre los hechos ocurridos el día 12 de marzo.' },
      { tipo_diligencia: 'Peritaje Médico', fecha: '2024-03-17', mp_responsable: 'Dr. Ana García Torres', numero_oficio: 'PERL/2024/022', resumen: 'Dictamen pericial sobre lesiones presentadas por la víctima. Conclusión: lesiones graves compatibles con instrumento contundente.' },
      { tipo_diligencia: 'Desahogo de Testigo', fecha: '2024-04-02', mp_responsable: 'Lic. María Ramírez', numero_oficio: 'TEST/2024/007', resumen: 'Declaración del testigo presencial Roberto Silva quien afirma haber visto al imputado en el lugar de los hechos.' },
      { tipo_diligencia: 'Inspección Ocular', fecha: '2024-04-10', mp_responsable: 'Lic. Carlos Mendoza Ruiz', numero_oficio: 'INSP/2024/015', resumen: 'Inspección del lugar de los hechos ubicado en Av. Revolución 445. Se encontraron indicios de interés criminalístico.' },
      { tipo_diligencia: 'Careo', fecha: '2024-05-08', mp_responsable: 'Lic. Jorge Pérez', numero_oficio: 'CAR/2024/003', resumen: 'Careo entre el imputado y el testigo Roberto Silva. Ambos mantienen sus versiones contradictorias.' },
    ],
  },
  2: {
    estado_analisis: 'pendiente', progreso: 0,
    estadisticas: null, alertas_mp: [], diligencias: [],
  },
  3: {
    estado_analisis: 'pendiente', progreso: 0,
    estadisticas: null, alertas_mp: [], diligencias: [],
  },
}

// Datos de análisis avanzado por tomo
const ANALISIS_AVANZADO = {
  1: {
    resumen: { total_fechas: 12, total_nombres: 8, total_direcciones: 3, total_lugares: 5, total_diligencias: 4, total_alertas: 1, paginas_analizadas: 45 },
    resultados: {
      fechas: [
        { tipo: 'actuacion', texto: '15 de marzo de 2024', dia: '15', mes: 'marzo', año: '2024', numero_pagina: 3 },
        { tipo: 'sentencia', texto: '22 de abril de 2024', dia: '22', mes: 'abril', año: '2024', numero_pagina: 12 },
        { tipo: 'nacimiento', texto: '5 de enero de 1985', dia: '5', mes: 'enero', año: '1985', numero_pagina: 7 },
      ],
      nombres: [
        { tipo: 'imputado', texto_completo: 'Juan López Martínez', nombres: 'Juan', apellido_paterno: 'López', apellido_materno: 'Martínez', numero_pagina: 1 },
        { tipo: 'ministerio_publico', texto_completo: 'Lic. Carlos Mendoza Ruiz', titulo: 'Lic.', nombres: 'Carlos', apellido_paterno: 'Mendoza', apellido_materno: 'Ruiz', numero_pagina: 2 },
        { tipo: 'testigo', texto_completo: 'Roberto Silva Hernández', nombres: 'Roberto', apellido_paterno: 'Silva', apellido_materno: 'Hernández', numero_pagina: 18 },
      ],
      direcciones: [
        { tipo: 'domicilio', texto: 'Av. Revolución 445, Col. Centro, CDMX', tipo_via: 'Av.', nombre_via: 'Revolución', numero: '445', colonia: 'Centro', codigo_postal: '06000', numero_pagina: 9 },
        { tipo: 'lugar_hechos', texto: 'Calle Morelos 23 Int. 4, Col. Guerrero', tipo_via: 'Calle', nombre_via: 'Morelos', numero: '23 Int. 4', colonia: 'Guerrero', numero_pagina: 5 },
      ],
      lugares: [
        { tipo: 'juzgado', texto: 'Juzgado Primero Penal de la Ciudad de México', nombre: 'Juzgado 1° Penal CDMX', numero_pagina: 1 },
        { tipo: 'municipio', texto: 'Ciudad de México', nombre: 'CDMX', numero_pagina: 3 },
        { tipo: 'colegio_abogados', texto: 'Barra Mexicana de Abogados', nombre: 'BMA', numero_pagina: 15 },
      ],
      diligencias: [
        { tipo: 'declaracion', texto_encontrado: 'Declaración ministerial del imputado', contexto: 'El Agente del Ministerio Público procedió a tomar la declaración del imputado quien manifestó desconocer los hechos...', numero_pagina: 4 },
        { tipo: 'peritaje', texto_encontrado: 'Dictamen pericial médico forense', contexto: 'Se solicitó la intervención del perito médico legista para certificar las lesiones...', numero_pagina: 8 },
        { tipo: 'inspeccion', texto_encontrado: 'Inspección ocular del lugar de los hechos', contexto: 'Constatado el lugar de los hechos con la presencia del Ministerio Público y la Policía Ministerial...', numero_pagina: 11 },
      ],
      alertas: [
        { tipo: 'inactividad', descripcion: 'No se registran actuaciones por más de 60 días entre el 22-abr y el 01-jul de 2024', texto_encontrado: '60 días sin actuaciones ministeriales', numero_pagina: 23 },
      ],
    },
  },
}

const TOMOS = {
  1: [
    { id: 1, nombre: 'Tomo 1 — Declaración inicial', carpeta_id: 1, total_paginas: 45, paginas_procesadas: 45, estado_ocr: 'completado', confianza_promedio: 94.2 },
    { id: 2, nombre: 'Tomo 2 — Peritajes',           carpeta_id: 1, total_paginas: 82, paginas_procesadas: 80, estado_ocr: 'procesando', confianza_promedio: 87.5 },
    { id: 3, nombre: 'Tomo 3 — Testigos',            carpeta_id: 1, total_paginas: 30, paginas_procesadas: 0,  estado_ocr: 'pendiente',  confianza_promedio: 0    },
  ],
  2: [
    { id: 4, nombre: 'Tomo 1 — Denuncia',            carpeta_id: 2, total_paginas: 20, paginas_procesadas: 20, estado_ocr: 'completado', confianza_promedio: 96.1 },
    { id: 5, nombre: 'Tomo 2 — Evidencias',          carpeta_id: 2, total_paginas: 55, paginas_procesadas: 55, estado_ocr: 'completado', confianza_promedio: 91.3 },
  ],
  3: [
    { id: 6, nombre: 'Tomo 1 — Documentos fiscales', carpeta_id: 3, total_paginas: 100, paginas_procesadas: 60, estado_ocr: 'procesando', confianza_promedio: 89.0 },
  ],
}

const AUDITORIA = Array.from({ length: 20 }, (_, i) => ({
  id: i + 1,
  usuario: USERS[i % USERS.length].username,
  accion: ['LOGIN', 'VER_TOMO', 'BUSQUEDA', 'DESCARGA', 'LOGOUT'][i % 5],
  ip: `192.168.1.${10 + i}`,
  fecha: new Date(Date.now() - i * 3600000).toISOString(),
  descripcion: `Acción de prueba #${i + 1}`,
}))

// Permisos por usuario: { tomo_id → { ver, buscar, exportar } }
const ROLE_PERMISOS = {
  1: null, // admin: acceso total, no se filtra
  2: {     // juan: permisos limitados (analista)
    1: { ver: true,  buscar: true,  exportar: true  },
    2: { ver: true,  buscar: true,  exportar: false },
    4: { ver: true,  buscar: false, exportar: false },
  },
  3: {     // maria: solo ver
    1: { ver: true,  buscar: false, exportar: false },
    4: { ver: true,  buscar: false, exportar: false },
    5: { ver: true,  buscar: true,  exportar: false },
  },
  4: null, // supervisor: acceso total
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function json(res, data, status = 200) {
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  })
  res.end(JSON.stringify(data))
}

function readBody(req) {
  return new Promise(resolve => {
    let body = ''
    req.on('data', chunk => body += chunk)
    req.on('end', () => { try { resolve(JSON.parse(body || '{}')) } catch { resolve({}) } })
  })
}

function getUser(req) {
  const auth = req.headers.authorization || ''
  const token = auth.replace('Bearer ', '')
  if (!token) return null
  // token format: "mock-token-<userId>"
  const id = parseInt(token.split('-').pop())
  return USERS.find(u => u.id === id) || null
}

// ── Router ───────────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  const url = req.url.split('?')[0]
  const qs  = new URLSearchParams(req.url.includes('?') ? req.url.split('?')[1] : '')
  const method = req.method

  // CORS preflight
  if (method === 'OPTIONS') { json(res, {}); return }

  console.log(`[${method}] ${req.url}`)

  // ── Auth ────────────────────────────────────────────────────────────────
  if (method === 'POST' && url === '/api/auth/login') {
    const body = await readBody(req)
    const user = USERS.find(u => u.username === body.username)
    if (!user) return json(res, { detail: 'Usuario o contraseña incorrectos' }, 401)
    // Aceptar cualquier contraseña en modo mock
    return json(res, {
      access_token: `mock-token-${user.id}`,
      token_type: 'bearer',
      user: { id: user.id, username: user.username, nombre: user.nombre, email: user.email, rol: user.rol?.nombre ?? user.rol }
    })
  }

  if ((method === 'GET') && (url === '/api/auth/me' || url === '/api/test-auth')) {
    const u = getUser(req)
    if (!u) return json(res, { detail: 'No autenticado' }, 401)
    return json(res, { id: u.id, username: u.username, nombre: u.nombre, email: u.email, rol: u.rol?.nombre ?? u.rol })
  }

  if (method === 'POST' && url === '/api/auth/refresh') {
    const u = getUser(req)
    if (!u) return json(res, { detail: 'Token inválido' }, 401)
    return json(res, { access_token: `mock-token-${u.id}`, token_type: 'bearer' })
  }

  // ── Carpetas ────────────────────────────────────────────────────────────
  if (method === 'GET' && url === '/api/carpetas') {
    return json(res, CARPETAS)
  }

  if (method === 'POST' && url === '/api/carpetas') {
    const body = await readBody(req)
    const nueva = { id: CARPETAS.length + 1, nombre: body.nombre || 'Nueva carpeta', descripcion: body.descripcion || '', total_tomos: 0, tomos_procesados: 0 }
    CARPETAS.push(nueva)
    return json(res, nueva, 201)
  }

  const carpetaMatch = url.match(/^\/api\/carpetas\/(\d+)$/)
  if (carpetaMatch) {
    const id = parseInt(carpetaMatch[1])
    const c = CARPETAS.find(c => c.id === id)
    if (method === 'GET')    return c ? json(res, c) : json(res, { detail: 'No encontrada' }, 404)
    if (method === 'PUT') {
      const body = await readBody(req); Object.assign(c, body)
      return json(res, c)
    }
    if (method === 'DELETE') {
      CARPETAS.splice(CARPETAS.findIndex(c => c.id === id), 1)
      return json(res, { ok: true })
    }
  }

  // ── Tomos ────────────────────────────────────────────────────────────────
  const tomosMatch = url.match(/^\/api\/tomos\/(\d+)$/)
  if (method === 'GET' && tomosMatch) {
    const id = parseInt(tomosMatch[1])
    const lista = TOMOS[id]
    if (lista) return json(res, lista)
    // Buscar tomo individual por id
    const tomo = Object.values(TOMOS).flat().find(t => t.id === id)
    return tomo ? json(res, tomo) : json(res, { detail: 'No encontrado' }, 404)
  }

  if (method === 'GET' && url === '/api/tomos') {
    return json(res, { items: Object.values(TOMOS).flat(), total: 6 })
  }

  if (method === 'GET' && url === '/api/tomos/usuario/permisos') {
    return json(res, { tomos: Object.values(TOMOS).flat() })
  }

  const tomoAnalisisMatch = url.match(/^\/api\/tomos\/(\d+)\/analisis-avanzado$/)
  if (tomoAnalisisMatch) {
    const tid = parseInt(tomoAnalisisMatch[1])
    const data = ANALISIS_AVANZADO[tid]
    if (data) return json(res, data)
    // Generar datos genéricos si el tomo no tiene análisis guardado
    return json(res, {
      resumen: { total_fechas: 4, total_nombres: 3, total_direcciones: 1, total_lugares: 2, total_diligencias: 2, total_alertas: 0, paginas_analizadas: 20 },
      resultados: {
        fechas: [{ tipo: 'actuacion', texto: '10 de junio de 2024', dia: '10', mes: 'junio', año: '2024', numero_pagina: 2 }],
        nombres: [{ tipo: 'implicado', texto_completo: 'Persona Ejemplo Apellido', nombres: 'Persona', apellido_paterno: 'Ejemplo', apellido_materno: 'Apellido', numero_pagina: 1 }],
        direcciones: [],
        lugares: [{ tipo: 'municipio', texto: 'Ciudad de México', nombre: 'CDMX', numero_pagina: 1 }],
        diligencias: [{ tipo: 'declaracion', texto_encontrado: 'Diligencia ejemplo encontrada en el texto', contexto: 'Contexto de ejemplo para la diligencia detectada en el documento procesado...', numero_pagina: 3 }],
        alertas: [],
      },
    })
  }

  const tomoStatsMatch = url.match(/^\/api\/tomos\/(\d+)\/estadisticas-ocr-avanzadas$/)
  if (tomoStatsMatch) {
    const id = parseInt(tomoStatsMatch[1])
    const tomo = Object.values(TOMOS).flat().find(t => t.id === id)
    return json(res, { total_paginas: tomo?.total_paginas || 45, paginas_con_texto: tomo?.paginas_procesadas || 40, confianza_promedio: tomo?.confianza_promedio || 92, total_palabras: 12340 })
  }

  // ── Búsqueda ─────────────────────────────────────────────────────────────
  if (method === 'GET' && url.startsWith('/api/analisis/tomos')) {
    return json(res, Object.values(TOMOS).flat())
  }

  // ── Usuarios admin ───────────────────────────────────────────────────────
  if (method === 'GET' && url === '/api/admin/usuarios') {
    return json(res, USERS)
  }

  if (method === 'GET' && url === '/api/admin/roles') {
    return json(res, [
      { id: 1, nombre: 'admin' },
      { id: 2, nombre: 'usuario' },
      { id: 3, nombre: 'supervisor' },
    ])
  }

  if (method === 'POST' && url === '/api/admin/usuarios') {
    const body = await readBody(req)
    const nuevoUser = {
      id: USERS.length + 1,
      username: body.username,
      nombre: body.nombre || '',
      email: body.email || '',
      rol: { id: 2, nombre: body.rol || 'usuario' },
      activo: body.activo !== false,
      ultimo_acceso: null,
    }
    USERS.push(nuevoUser)
    return json(res, nuevoUser, 201)
  }

  const usuarioMatch = url.match(/^\/api\/admin\/usuarios\/(\d+)$/)
  if (usuarioMatch) {
    const id = parseInt(usuarioMatch[1])
    const u = USERS.find(u => u.id === id)
    if (method === 'GET')    return u ? json(res, u) : json(res, { detail: 'No encontrado' }, 404)
    if (method === 'PUT') {
      const body = await readBody(req); if (u) Object.assign(u, body)
      return json(res, u || {})
    }
    if (method === 'DELETE') {
      const idx = USERS.findIndex(u => u.id === id)
      if (idx >= 0) USERS.splice(idx, 1)
      return json(res, { ok: true })
    }
  }

  // ── Permisos ─────────────────────────────────────────────────────────────
  const permisosDelMatch = url.match(/^\/api\/permisos\/usuarios\/(\d+)\/tomos\/(\d+)$/)
  if (permisosDelMatch && method === 'DELETE') {
    const uid = parseInt(permisosDelMatch[1])
    const tid = parseInt(permisosDelMatch[2])
    if (ROLE_PERMISOS[uid]) delete ROLE_PERMISOS[uid][tid]
    return json(res, { ok: true })
  }

  const permisosPostMatch = url.match(/^\/api\/permisos\/usuarios\/(\d+)\/tomos$/)
  if (permisosPostMatch && method === 'POST') {
    const uid = parseInt(permisosPostMatch[1])
    const body = await readBody(req)
    if (!ROLE_PERMISOS[uid]) ROLE_PERMISOS[uid] = {}
    ROLE_PERMISOS[uid][body.tomo_id] = {
      ver:      body.ver      !== false,
      buscar:   body.buscar   !== false,
      exportar: body.exportar !== false,
    }
    return json(res, { ok: true, tomo_id: body.tomo_id })
  }

  const permisosMatch = url.match(/^\/api\/permisos\/usuarios\/(\w+)/)
  if (permisosMatch) {
    let uid
    if (permisosMatch[1] === 'me') {
      const u = getUser(req)
      uid = u?.id
    } else {
      uid = parseInt(permisosMatch[1])
    }
    const tomosList = Object.values(TOMOS).flat()
    const mapa = ROLE_PERMISOS[uid]  // null = acceso total

    return json(res, tomosList.map(t => ({
      tomo_id:   t.id,
      nombre:    t.nombre,
      carpeta_id: t.carpeta_id,
      ver:      mapa ? !!(mapa[t.id]?.ver)      : true,
      buscar:   mapa ? !!(mapa[t.id]?.buscar)   : true,
      exportar: mapa ? !!(mapa[t.id]?.exportar) : true,
    })))
  }

  // ── Auditoría ────────────────────────────────────────────────────────────
  if (method === 'GET' && url.startsWith('/api/auditoria')) {
    if (url.includes('usuarios-activos')) return json(res, { usuarios_activos: 3 })
    const pagina = parseInt(qs.get('pagina') || '1')
    return json(res, { items: AUDITORIA, total: AUDITORIA.length, pagina, total_paginas: 2 })
  }

  // ── OCR Stats / Monitor ───────────────────────────────────────────────────
  if (method === 'GET' && url.startsWith('/api/ocr/stats')) {
    return json(res, { paginas_procesadas: 40, total_paginas: 45, confianza: 94.2, estado: 'completado' })
  }

  if (method === 'GET' && url.startsWith('/api/ocr/quality')) {
    return json(res, { calidad: 'alta', errores: 2, advertencias: 5 })
  }

  // ── Análisis IA — carpetas con estado ────────────────────────────────────
  if (method === 'GET' && url === '/api/admin/carpetas-analisis') {
    const lista = CARPETAS.map(c => ({
      ...c,
      ...(ANALISIS_ESTADO[c.id] || { estado_analisis: 'pendiente', progreso: 0 }),
      estadisticas: ANALISIS_ESTADO[c.id]?.estadisticas || null,
    }))
    return json(res, lista)
  }

  const iniciarAnalisisMatch = url.match(/^\/api\/admin\/carpetas\/(\d+)\/iniciar-analisis$/)
  if (iniciarAnalisisMatch && method === 'POST') {
    const cid = parseInt(iniciarAnalisisMatch[1])
    if (!ANALISIS_ESTADO[cid]) ANALISIS_ESTADO[cid] = { estado_analisis: 'pendiente', progreso: 0, estadisticas: null, alertas_mp: [], diligencias: [] }
    ANALISIS_ESTADO[cid].estado_analisis = 'procesando'
    ANALISIS_ESTADO[cid].progreso = 0
    // Simular completado tras 5s
    setTimeout(() => {
      if (ANALISIS_ESTADO[cid].estado_analisis === 'procesando') {
        ANALISIS_ESTADO[cid].estado_analisis = 'completado'
        ANALISIS_ESTADO[cid].progreso = 100
        if (!ANALISIS_ESTADO[cid].estadisticas) {
          ANALISIS_ESTADO[cid].estadisticas = { total_diligencias: 3, total_personas: 6, total_lugares: 2, total_fechas: 9, total_alertas_activas: 0 }
          ANALISIS_ESTADO[cid].diligencias = [
            { tipo_diligencia: 'Diligencia Mock', fecha: new Date().toISOString().slice(0,10), mp_responsable: 'MP Mock', numero_oficio: 'OF/2024/001', resumen: 'Diligencia generada automáticamente para carpeta ' + cid },
          ]
        }
      }
    }, 5000)
    return json(res, { ok: true, mensaje: 'Análisis iniciado. Se completará en breves momentos.' })
  }

  const estadisticasCarpetaMatch = url.match(/^\/api\/admin\/carpetas\/(\d+)\/estadisticas$/)
  if (estadisticasCarpetaMatch && method === 'GET') {
    const cid = parseInt(estadisticasCarpetaMatch[1])
    const estado = ANALISIS_ESTADO[cid] || {}
    return json(res, { ...(estado.estadisticas || {}), alertas_mp: estado.alertas_mp || [] })
  }

  const diligenciasCarpetaMatch = url.match(/^\/api\/usuario\/carpetas\/(\d+)\/diligencias$/)
  if (diligenciasCarpetaMatch && method === 'GET') {
    const cid = parseInt(diligenciasCarpetaMatch[1])
    return json(res, (ANALISIS_ESTADO[cid] || {}).diligencias || [])
  }

  // ── Dashboard stats ───────────────────────────────────────────────────────
  if (method === 'GET' && url.startsWith('/api/admin/carpetas')) {
    return json(res, CARPETAS)
  }

  // ── Análisis jurídico ─────────────────────────────────────────────────────
  if (method === 'POST' && url.startsWith('/api/analisis-juridico')) {
    const body = await readBody(req)
    return json(res, {
      resumen: 'El texto hace referencia a un proceso penal con evidencias documentales.',
      entidades: ['Juan López Martínez', 'Ministerio Público', 'Ciudad de México'],
      fechas: ['15 de marzo de 2024', '22 de abril de 2024'],
      tipo_delito: 'Robo calificado',
      gravedad: 'alta',
      recomendacion: 'Se sugiere ampliar diligencias con testigos adicionales.',
      texto_analizado: body.texto?.substring(0, 100) || ''
    })
  }

  // ── Búsqueda semántica ────────────────────────────────────────────────────
  if (method === 'POST' && url === '/api/busqueda/semantica') {
    const body = await readBody(req)
    return json(res, {
      resultados: [
        { id: 1, tomo: 'Tomo 1 — Declaración inicial', carpeta: 'Carpeta 001', similitud: 0.94, fragmento: `…texto relacionado con "${body.query || 'búsqueda'}"…` },
        { id: 2, tomo: 'Tomo 2 — Peritajes',           carpeta: 'Carpeta 001', similitud: 0.87, fragmento: '…evidencias documentales del caso…' },
      ]
    })
  }

  // ── Autocorrector ─────────────────────────────────────────────────────────
  if (method === 'POST' && url === '/api/autocorrector/corregir-texto') {
    const body = await readBody(req)
    return json(res, {
      texto_corregido: (body.texto || '').replace(/q /g, 'que ').replace(/xq/g, 'porque'),
      correcciones: [{ original: 'q', corregido: 'que' }, { original: 'xq', corregido: 'porque' }]
    })
  }

  // ── Tomos: subir (multipart) ────────────────────────────────────────────
  if (method === 'POST' && url === '/api/tomos/subir') {
    // En modo mock ignoramos el body multipart y devolvemos un tomo fake
    const carpetaId = parseInt(qs.get('carpeta_id') || '1')
    const nuevoTomo = {
      id: Date.now(),
      nombre: 'Tomo nuevo (mock)',
      numero_tomo: 99,
      carpeta_id: carpetaId,
      total_paginas: 0,
      paginas_procesadas: 0,
      estado: 'pendiente',
      estado_ocr: 'pendiente',
      confianza_promedio: 0,
    }
    if (!TOMOS[carpetaId]) TOMOS[carpetaId] = []
    TOMOS[carpetaId].push(nuevoTomo)
    return json(res, nuevoTomo, 201)
  }

  // ── Tomos: procesar OCR ───────────────────────────────────────────────────
  const ocrProcesar = url.match(/^\/api\/tomos\/(\d+)\/procesar-ocr$/)
  if (ocrProcesar && method === 'POST') {
    const tid = parseInt(ocrProcesar[1])
    const tomo = Object.values(TOMOS).flat().find(t => t.id === tid)
    if (tomo) { tomo.estado = 'procesando'; tomo.estado_ocr = 'procesando' }
    return json(res, { ok: true, mensaje: 'OCR iniciado', tomo_id: tid })
  }

  // ── Tomos: texto OCR de una página ───────────────────────────────────────
  const ocrPaginaMatch = url.match(/^\/api\/tomos\/ocr\/(\d+)\/pagina\/(\d+)$/)
  if (ocrPaginaMatch && method === 'GET') {
    const tomoId = ocrPaginaMatch[1]
    const page   = ocrPaginaMatch[2]
    return json(res, {
      texto: `[Texto OCR mock — Tomo ${tomoId}, Página ${page}]\n\nEn uso del ejercicio de sus funciones, el Ministerio Público procedió a realizar las diligencias correspondientes conforme a lo establecido en el Código Nacional de Procedimientos Penales...`,
      pagina: parseInt(page),
      confianza: 92.5,
    })
  }

  // ── Tomos: descargar / PDF blob ───────────────────────────────────────────
  const descargarMatch = url.match(/^\/api\/tomos\/(\d+)\/descargar$/)
  const pdfMatch       = url.match(/^\/api\/tomos\/(\d+)\/pdf$/)
  if ((descargarMatch || pdfMatch) && method === 'GET') {
    // Redirigir a un PDF público de muestra
    res.writeHead(302, {
      'Location': 'https://www.w3.org/WAI/WCAG21/Techniques/pdf/sample.pdf',
      'Access-Control-Allow-Origin': '*',
    })
    res.end()
    return
  }

  // ── Health check ──────────────────────────────────────────────────────────
  if (url === '/health' || url === '/api/health') {
    return json(res, { status: 'ok', mode: 'mock', version: '1.0.0' })
  }

  // ── Default: 200 vacío para rutas no implementadas ────────────────────────
  json(res, { items: [], total: 0, mock: true })
})

server.listen(8000, () => {
  console.log('╔══════════════════════════════════════════════╗')
  console.log('║  🟢 Mock API corriendo en http://localhost:8000  ║')
  console.log('║  Frontend Vue en http://localhost:5173       ║')
  console.log('╠══════════════════════════════════════════════╣')
  console.log('║  Usuarios de prueba (cualquier contraseña):  ║')
  console.log('║  • admin       → rol: admin                  ║')
  console.log('║  • juan        → rol: usuario                ║')
  console.log('║  • maria       → rol: usuario                ║')
  console.log('║  • supervisor  → rol: supervisor             ║')
  console.log('╚══════════════════════════════════════════════╝')
})
