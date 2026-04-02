<template>
  <div class="pdf-container">
    <!-- ══ TOOLBAR ══ -->
    <div class="pdf-toolbar">
      <div class="tomo-info" v-if="tomoNombre">
        📄 <span>{{ tomoNombre }}</span>
      </div>

      <button @click="router.back()" class="tb-btn">◄ Volver</button>

      <button :disabled="pageNum <= 1" @click="prevPage()" class="tb-btn">◄ Anterior</button>
      <div class="page-info">
        Página
        <input
          type="number" v-model.number="pageInputVal" min="1"
          :max="totalPages"
          @keydown.enter="irAPagina(pageInputVal)"
          @change="irAPagina(pageInputVal)"
          class="page-input"
        />
        de <strong>{{ totalPages }}</strong>
      </div>
      <button :disabled="pageNum >= totalPages" @click="nextPage()" class="tb-btn">Siguiente ►</button>

      <div class="zoom-controls">
        <button @click="zoomOut()" class="tb-btn" title="Reducir (-)">🔍-</button>
        <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
        <button @click="zoomIn()" class="tb-btn" title="Aumentar (+)">🔍+</button>
        <button @click="fitToWidth()" class="tb-btn">⬌ Ajustar</button>
      </div>

      <!-- Botón Google Lens -->
      <button
        @click="toggleLens()"
        class="tb-btn lens-btn"
        :class="{ active: lensMode }"
        title="Selección inteligente — arrastra sobre el texto"
      >
        🔍 {{ lensMode ? '✅ Lens Activo' : 'Selección Inteligente' }}
      </button>

      <button @click="copiarPagina()" class="tb-btn" title="Copiar todo el texto de esta página">📄 Copiar Página</button>
    </div>

    <!-- ══ VISOR ══ -->
    <div class="pdf-viewer" id="pdf-viewer" ref="viewerEl">
      <!-- Cargando initial -->
      <div v-if="!pdfLoaded && !pdfError" class="loading-center">
        <div class="spinner"></div>
        <p>Cargando documento...</p>
      </div>
      <div v-if="pdfError" class="loading-center error-txt">
        ❌ {{ pdfError }}
      </div>

      <!-- Canvas + capa de texto -->
      <div class="page-wrap" v-show="pdfLoaded" ref="pageWrapEl">
        <canvas id="pdf-canvas" ref="canvasEl"></canvas>
        <!-- Capa de texto seleccionable (estilo real PDF viewer) -->
        <div id="text-layer" ref="textLayerEl" class="text-layer"></div>
        <!-- Overlay de selección Lens -->
        <div v-if="lensMode || lensSelecting" class="lens-overlay-box" ref="lensBoxEl"></div>
      </div>
    </div>

    <!-- ══ TOOLTIP RESULTADO LENS ══ -->
    <Teleport to="body">
      <div v-if="lensResult.visible" class="lens-result-panel" :style="lensResult.style">
        <div class="lr-header">
          <span>🔍 Texto extraído ({{ lensResult.confidence }}% confianza)</span>
          <button @click="lensResult.visible = false">✕</button>
        </div>
        <div class="lr-text">{{ lensResult.text }}</div>
        <div class="lr-actions">
          <button @click="copiarLensText()" class="lr-btn primary">📋 Copiar</button>
          <button @click="buscarLensText()" class="lr-btn">🔍 Buscar Google</button>
          <button @click="escucharLensText()" class="lr-btn">🔊 Escuchar</button>
          <button @click="lensResult.visible = false" class="lr-btn">✕ Cerrar</button>
        </div>
      </div>
    </Teleport>

    <!-- ══ MENÚ CONTEXTUAL ══ -->
    <Teleport to="body">
      <div v-if="contextMenu.visible" class="context-menu" :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }" @click.stop>
        <div class="cm-item" @click="activarLens(); contextMenu.visible = false">🔍 Seleccionar área (Lens)</div>
        <div class="cm-sep"></div>
        <div class="cm-item" @click="copiarTextoSeleccionado(); contextMenu.visible = false">📋 Copiar texto seleccionado</div>
        <div class="cm-item" @click="copiarPagina(); contextMenu.visible = false">📄 Copiar toda la página</div>
        <div class="cm-sep"></div>
        <div class="cm-item" @click="fitToWidth(); contextMenu.visible = false">⬌ Ajustar a ventana</div>
        <div class="cm-item" @click="mostrarInfoDoc(); contextMenu.visible = false">ℹ️ Info del documento</div>
      </div>
    </Teleport>

    <!-- ══ BANNER AYUDA ══ -->
    <Teleport to="body">
      <div v-if="bannerVisible" class="help-banner">
        <button class="banner-close" @click="cerrarBanner()">✕</button>
        <h4>💡 Cómo copiar texto del PDF</h4>
        <ul>
          <li><strong>Clic derecho:</strong> Menú con opciones</li>
          <li><strong>Selección Inteligente:</strong> Arrastra para seleccionar área → OCR automático</li>
          <li><strong>Copiar Página:</strong> Obtiene todo el texto de la página actual</li>
          <li><strong>Texto seleccionable:</strong> Arrastra con el mouse sobre el texto</li>
        </ul>
      </div>
    </Teleport>

    <!-- Toast notificación -->
    <Teleport to="body">
      <div v-if="toastMsg" class="pdf-toast" :class="toastType">{{ toastMsg }}</div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const API_BASE = import.meta.env.VITE_API_URL || '/api'

// ── Refs DOM ─────────────────────────────────────────────────────────────────
const canvasEl   = ref(null)
const textLayerEl = ref(null)
const lensBoxEl  = ref(null)
const pageWrapEl = ref(null)
const viewerEl   = ref(null)

// ── Estado PDF ────────────────────────────────────────────────────────────────
let pdfDoc = null
let renderTask = null
const pdfLoaded  = ref(false)
const pdfError   = ref('')
const totalPages = ref(0)
const pageNum    = ref(1)
const pageInputVal = ref(1)
const scale      = ref(1.5)
const tomoId     = ref(route.query.tomo_id || null)
const tomoNombre = ref(route.query.nombre || 'Documento')

// ── Lens OCR ──────────────────────────────────────────────────────────────────
const lensMode        = ref(false)
const lensSelecting   = ref(false)
let lensStart = { x: 0, y: 0 }
let lensEnd   = { x: 0, y: 0 }
let tesseractWorker   = null
const lensResult = reactive({ visible: false, text: '', confidence: 0, style: {} })

// ── Menú contextual ───────────────────────────────────────────────────────────
const contextMenu = reactive({ visible: false, x: 0, y: 0 })

// ── Banner ayuda ──────────────────────────────────────────────────────────────
const bannerVisible = ref(false)

// ── Toast ────────────────────────────────────────────────────────────────────
let toastTimer = null
const toastMsg  = ref('')
const toastType = ref('info')

// ── Init ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  if (!auth.token) { router.push({ name: 'login' }); return }
  if (!tomoId.value) { pdfError.value = 'No se especificó el documento'; return }

  // Mostrar banner ayuda (primera vez)
  if (!localStorage.getItem('pdf_help_seen')) {
    setTimeout(() => {
      bannerVisible.value = true
      setTimeout(() => cerrarBanner(), 10000)
    }, 1500)
  }

  await cargarPDF()
  await initTesseract()
  setupContextMenu()
  setupKeyboard()
})

onUnmounted(() => {
  if (tesseractWorker) tesseractWorker.terminate().catch(() => {})
  document.removeEventListener('contextmenu', onContextMenu)
  document.removeEventListener('click', cerrarMenus)
  document.removeEventListener('keydown', onKeydown)
})

// ── Cargar PDF ────────────────────────────────────────────────────────────────
async function cargarPDF() {
  try {
    const pdfUrl = `${API_BASE}/tomos/${tomoId.value}/pdf`
    const response = await fetch(pdfUrl, {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    if (!response.ok) throw new Error(`Error al cargar el PDF (${response.status})`)

    const blob = await response.blob()
    const objectUrl = URL.createObjectURL(blob)

    // Cargar con PDF.js
    const loadingTask = window.pdfjsLib.getDocument(objectUrl)
    pdfDoc = await loadingTask.promise
    totalPages.value = pdfDoc.numPages

    // Página inicial desde URL si viene especificada
    const paginaInicial = parseInt(route.query.page || '1')
    pageNum.value = Math.max(1, Math.min(paginaInicial, totalPages.value))
    pageInputVal.value = pageNum.value

    pdfLoaded.value = true
    await renderPage(pageNum.value)
  } catch (e) {
    pdfError.value = e.message
  }
}

// ── Render página ─────────────────────────────────────────────────────────────
async function renderPage(num) {
  if (!pdfDoc) return
  if (renderTask) { renderTask.cancel(); renderTask = null }

  const page = await pdfDoc.getPage(num)
  const viewport = page.getViewport({ scale: scale.value })

  const canvas = canvasEl.value
  const ctx    = canvas.getContext('2d')
  canvas.width  = viewport.width
  canvas.height = viewport.height

  pageWrapEl.value.style.width  = viewport.width + 'px'
  pageWrapEl.value.style.height = viewport.height + 'px'

  renderTask = page.render({ canvasContext: ctx, viewport })
  try {
    await renderTask.promise
  } catch (e) {
    if (e.name !== 'RenderingCancelledException') console.error(e)
    return
  }
  renderTask = null

  // Capa de texto seleccionable
  await buildTextLayer(page, viewport)

  pageNum.value     = num
  pageInputVal.value = num
}

async function buildTextLayer(page, viewport) {
  const tl = textLayerEl.value
  tl.innerHTML = ''
  tl.style.width  = viewport.width + 'px'
  tl.style.height = viewport.height + 'px'

  const textContent = await page.getTextContent()

  // Usar la API de PDF.js para renderizar la capa de texto
  if (window.pdfjsLib.renderTextLayer) {
    window.pdfjsLib.renderTextLayer({
      textContentSource: textContent,
      container: tl,
      viewport,
      textDivs: [],
    })
  } else {
    // Fallback manual
    textContent.items.forEach(item => {
      const tx = window.pdfjsLib.Util?.transform || ((a, b) => [
        a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
        a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
        a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]
      ])
      const fontHeight = Math.sqrt(item.transform[2]**2 + item.transform[3]**2)
      const [,, , , x, y] = tx(viewport.transform, item.transform)
      const span = document.createElement('span')
      span.textContent = item.str
      span.style.cssText = `position:absolute;left:${x}px;top:${viewport.height-(y+fontHeight)}px;font-size:${fontHeight}px;transform-origin:0% 0%;white-space:pre;color:transparent;cursor:text;`
      tl.appendChild(span)
    })
  }
}

// ── Navegación y zoom ─────────────────────────────────────────────────────────
async function prevPage() { if (pageNum.value > 1) await renderPage(pageNum.value - 1) }
async function nextPage() { if (pageNum.value < totalPages.value) await renderPage(pageNum.value + 1) }

async function irAPagina(n) {
  n = parseInt(n)
  if (!isNaN(n) && n >= 1 && n <= totalPages.value) await renderPage(n)
  else pageInputVal.value = pageNum.value
}

function zoomIn()  { scale.value = Math.min(scale.value + 0.25, 4);    renderPage(pageNum.value) }
function zoomOut() { scale.value = Math.max(scale.value - 0.25, 0.5);  renderPage(pageNum.value) }

function fitToWidth() {
  const viewerW = viewerEl.value?.clientWidth || 800
  if (!canvasEl.value) { scale.value = 1.5; return }
  const pdfPageW = canvasEl.value.width / scale.value
  scale.value = Math.max(0.5, (viewerW - 60) / pdfPageW)
  renderPage(pageNum.value)
}

// ── Tesseract ─────────────────────────────────────────────────────────────────
async function initTesseract() {
  try {
    if (!window.Tesseract) return
    tesseractWorker = await window.Tesseract.createWorker({
      logger: m => {
        if (m.status === 'recognizing text') {
          const pct = Math.round(m.progress * 100)
          showToast(`🔍 OCR: ${pct}%...`, 'info', 30000)
        }
      }
    })
    await tesseractWorker.loadLanguage('spa')
    await tesseractWorker.initialize('spa')
    await tesseractWorker.setParameters({
      tessedit_pageseg_mode: window.Tesseract.PSM.AUTO,
    })
  } catch (e) {
    console.warn('Tesseract no disponible:', e)
  }
}

// ── Google Lens Mode ──────────────────────────────────────────────────────────
function toggleLens() { lensMode.value = !lensMode.value }
function activarLens() { lensMode.value = true }

watch(lensMode, (active) => {
  const canvas = canvasEl.value
  if (!canvas) return
  if (active) {
    canvas.style.cursor = 'crosshair'
    canvas.addEventListener('mousedown', onLensMouseDown)
    canvas.addEventListener('mousemove', onLensMouseMove)
    canvas.addEventListener('mouseup',   onLensMouseUp)
    showToast('🔍 Arrastra sobre el texto para extraerlo', 'info', 4000)
  } else {
    canvas.style.cursor = 'default'
    canvas.removeEventListener('mousedown', onLensMouseDown)
    canvas.removeEventListener('mousemove', onLensMouseMove)
    canvas.removeEventListener('mouseup',   onLensMouseUp)
    if (lensBoxEl.value) lensBoxEl.value.style.display = 'none'
  }
})

function onLensMouseDown(e) {
  if (!lensMode.value) return
  lensSelecting.value = true
  const rect = canvasEl.value.getBoundingClientRect()
  lensStart = { x: e.clientX - rect.left, y: e.clientY - rect.top }
  lensEnd = { ...lensStart }
  updateLensBox()
}

function onLensMouseMove(e) {
  if (!lensSelecting.value) return
  const rect = canvasEl.value.getBoundingClientRect()
  lensEnd = { x: e.clientX - rect.left, y: e.clientY - rect.top }
  updateLensBox()
}

async function onLensMouseUp(e) {
  if (!lensSelecting.value) return
  lensSelecting.value = false
  const rect = canvasEl.value.getBoundingClientRect()
  lensEnd = { x: e.clientX - rect.left, y: e.clientY - rect.top }

  const x = Math.min(lensStart.x, lensEnd.x)
  const y = Math.min(lensStart.y, lensEnd.y)
  const w = Math.abs(lensEnd.x - lensStart.x)
  const h = Math.abs(lensEnd.y - lensStart.y)

  if (w < 15 || h < 15) {
    if (lensBoxEl.value) lensBoxEl.value.style.display = 'none'
    return
  }

  await extraerTextoArea(x, y, w, h)
}

function updateLensBox() {
  const box = lensBoxEl.value
  if (!box) return
  const x = Math.min(lensStart.x, lensEnd.x)
  const y = Math.min(lensStart.y, lensEnd.y)
  const w = Math.abs(lensEnd.x - lensStart.x)
  const h = Math.abs(lensEnd.y - lensStart.y)
  box.style.cssText = `display:block;left:${x}px;top:${y}px;width:${w}px;height:${h}px;`
}

async function extraerTextoArea(x, y, w, h) {
  const canvas = canvasEl.value
  if (!canvas) return

  showToast('🔍 Analizando texto...', 'info', 30000)

  try {
    // Obtener imagen del área seleccionada
    const tempCanvas = document.createElement('canvas')
    tempCanvas.width = w * 4   // Escalar 4x para mejor OCR
    tempCanvas.height = h * 4
    const tempCtx = tempCanvas.getContext('2d')
    tempCtx.imageSmoothingEnabled = true
    tempCtx.imageSmoothingQuality = 'high'
    tempCtx.drawImage(canvas, x, y, w, h, 0, 0, tempCanvas.width, tempCanvas.height)

    // Mejorar contraste para OCR
    mejorarContraste(tempCtx, tempCanvas.width, tempCanvas.height)

    let texto = ''
    let confianza = 0

    if (tesseractWorker) {
      const result = await tesseractWorker.recognize(tempCanvas)
      texto = result.data.text.trim()
      confianza = Math.round(result.data.confidence)
    } else {
      // Fallback: extraer texto de la capa PDF.js
      texto = extraerTextoCapa(x, y, w, h)
      confianza = 95
    }

    if (texto) {
      // Mostrar resultado en panel
      const canvasRect = canvas.getBoundingClientRect()
      lensResult.text = limpiarTextoOCR(texto)
      lensResult.confidence = confianza
      lensResult.style = {
        top: (canvasRect.top + y + h + 10) + 'px',
        left: Math.min((canvasRect.left + x), window.innerWidth - 380) + 'px'
      }
      lensResult.visible = true
      showToast(`✅ Texto extraído (${confianza}% confianza)`, 'success')
    } else {
      showToast('⚠️ No se detectó texto en el área', 'warning')
    }
  } catch (e) {
    showToast('❌ Error al extraer texto: ' + e.message, 'error')
  } finally {
    if (lensBoxEl.value) lensBoxEl.value.style.display = 'none'
  }
}

function mejorarContraste(ctx, w, h) {
  const imageData = ctx.getImageData(0, 0, w, h)
  const data = imageData.data
  for (let i = 0; i < data.length; i += 4) {
    const gray = 0.299 * data[i] + 0.587 * data[i+1] + 0.114 * data[i+2]
    const val = gray > 128 ? 255 : 0
    data[i] = data[i+1] = data[i+2] = val
  }
  ctx.putImageData(imageData, 0, 0)
}

function extraerTextoCapa(x, y, w, h) {
  // Extraer texto de la capa seleccionable dentro del área
  const spans = textLayerEl.value?.querySelectorAll('span') || []
  const textos = []
  for (const span of spans) {
    const sl = parseFloat(span.style.left)
    const st = parseFloat(span.style.top)
    if (sl >= x - 5 && sl <= x + w + 5 && st >= y - 5 && st <= y + h + 5) {
      textos.push(span.textContent)
    }
  }
  return textos.join(' ')
}

function limpiarTextoOCR(texto) {
  return texto
    .replace(/\s+/g, ' ')
    .replace(/([.,;:!?])\1+/g, '$1')
    .trim()
}

// ── Copiar texto ──────────────────────────────────────────────────────────────
function copiarTextoSeleccionado() {
  const sel = window.getSelection()?.toString().trim()
  if (!sel) { showToast('❌ Selecciona texto primero', 'error'); return }
  navigator.clipboard.writeText(sel).then(
    () => showToast(`✅ Copiado: ${sel.substring(0, 60)}${sel.length > 60 ? '...' : ''}`, 'success'),
    () => showToast('❌ No se pudo copiar', 'error')
  )
}

async function copiarPagina() {
  showToast('⏳ Extrayendo texto de la página...', 'info', 5000)
  try {
    // 1. Intentar OCR del backend
    const res = await fetch(`${API_BASE}/tomos/ocr/${tomoId.value}/pagina/${pageNum.value}`, {
      headers: { Authorization: `Bearer ${auth.token}` }
    })
    if (res.ok) {
      const data = await res.json()
      const t = data.texto_extraido?.trim()
      if (t) {
        await navigator.clipboard.writeText(t)
        showToast(`✅ Copiado OCR: ${t.split(/\s+/).length} palabras`, 'success')
        return
      }
    }
  } catch {}

  // 2. Fallback: texto nativo PDF.js
  try {
    const page = await pdfDoc.getPage(pageNum.value)
    const tc = await page.getTextContent()
    const txt = tc.items.map(i => i.str).join(' ').trim()
    if (!txt) { showToast('❌ No hay texto en esta página (PDF escaneado sin OCR)', 'error'); return }
    await navigator.clipboard.writeText(txt)
    showToast(`✅ Copiado: ${txt.split(/\s+/).length} palabras`, 'success')
  } catch (e) {
    showToast('❌ Error al extraer texto: ' + e.message, 'error')
  }
}

async function copiarLensText() {
  if (!lensResult.text) return
  await navigator.clipboard.writeText(lensResult.text)
  showToast('✅ Copiado al portapapeles', 'success')
  lensResult.visible = false
}

function buscarLensText() {
  if (!lensResult.text) return
  window.open(`https://www.google.com/search?q=${encodeURIComponent(lensResult.text.substring(0, 200))}`, '_blank')
  lensResult.visible = false
}

function escucharLensText() {
  if (!lensResult.text || !window.speechSynthesis) return
  const utt = new SpeechSynthesisUtterance(lensResult.text)
  utt.lang = 'es-MX'
  window.speechSynthesis.speak(utt)
}

// ── Menú contextual ───────────────────────────────────────────────────────────
function setupContextMenu() {
  document.addEventListener('contextmenu', onContextMenu)
  document.addEventListener('click', cerrarMenus)
}

function onContextMenu(e) {
  const inPDF = canvasEl.value?.contains(e.target) || textLayerEl.value?.contains(e.target)
  if (!inPDF) return
  e.preventDefault()
  contextMenu.x = Math.min(e.clientX, window.innerWidth - 220)
  contextMenu.y = Math.min(e.clientY, window.innerHeight - 200)
  contextMenu.visible = true
}

function cerrarMenus() {
  contextMenu.visible = false
}

function mostrarInfoDoc() {
  showToast(`📄 ${tomoNombre.value} · Páginas: ${totalPages.value} · Página actual: ${pageNum.value}`, 'info', 5000)
}

// ── Teclado ───────────────────────────────────────────────────────────────────
function setupKeyboard() {
  document.addEventListener('keydown', onKeydown)
}

function onKeydown(e) {
  if (e.target.tagName === 'INPUT') return
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') nextPage()
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') prevPage()
  if (e.key === 'Escape') { lensMode.value = false; lensResult.visible = false; contextMenu.visible = false }
  if (e.key === '+' || e.key === '=') zoomIn()
  if (e.key === '-') zoomOut()
}

// ── Banner ayuda ──────────────────────────────────────────────────────────────
function cerrarBanner() {
  bannerVisible.value = false
  localStorage.setItem('pdf_help_seen', '1')
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info', duration = 3000) {
  toastMsg.value = msg
  toastType.value = type
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastMsg.value = '' }, duration)
}

// Cargar PDF.js y Tesseract.js si no están cargados
function loadScript(src) {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return }
    const s = document.createElement('script')
    s.src = src
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
}

// Pre-cargar PDF.js al iniciar el componente
;(async () => {
  if (!window.pdfjsLib) {
    await loadScript('https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js')
    window.pdfjsLib.GlobalWorkerOptions.workerSrc =
      'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'
  }
  if (!window.Tesseract) {
    loadScript('https://cdn.jsdelivr.net/npm/tesseract.js@4/dist/tesseract.min.js').catch(() => {})
  }
})()
</script>

<style scoped>
/* ── Layout ── */
.pdf-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #2c3e50;
  overflow: hidden;
}

/* ── Toolbar ── */
.pdf-toolbar {
  background: #1a365d;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  flex-wrap: wrap;
  flex-shrink: 0;
}

.tomo-info {
  background: rgba(255,255,255,0.1);
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tb-btn {
  background: #2c5aa0;
  color: white;
  border: none;
  padding: 8px 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition: background 0.2s, transform 0.1s;
  white-space: nowrap;
}
.tb-btn:hover:not(:disabled) { background: #1e3a8a; transform: translateY(-1px); }
.tb-btn:disabled { background: #64748b; cursor: not-allowed; opacity: 0.7; }

.lens-btn { background: #34a853; }
.lens-btn:hover:not(:disabled) { background: #2d8f47; }
.lens-btn.active { background: #1a6b30; border: 2px solid #34a853; }

.page-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}
.page-input {
  width: 56px;
  padding: 4px 6px;
  border: 2px solid #3b82f6;
  border-radius: 6px;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
  color: #1a365d;
}

.zoom-controls { display: flex; align-items: center; gap: 6px; }
.zoom-label { min-width: 50px; text-align: center; font-weight: 600; }

/* ── Visor ── */
.pdf-viewer {
  flex: 1;
  overflow: auto;
  background: #34495e;
  display: flex;
  justify-content: center;
  padding: 20px;
}

.loading-center {
  color: white;
  text-align: center;
  margin: auto;
}
.error-txt { color: #ff6b6b; }

.spinner {
  border: 4px solid rgba(255,255,255,0.3);
  border-top: 4px solid white;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
  margin: 0 auto 15px;
}
@keyframes spin { 100% { transform: rotate(360deg); } }

.page-wrap {
  position: relative;
  margin-bottom: 20px;
}

#pdf-canvas {
  display: block;
  box-shadow: 0 4px 24px rgba(0,0,0,0.6);
  background: white;
}

/* ── Capa de texto seleccionable ── */
.text-layer {
  position: absolute;
  left: 0; top: 0;
  overflow: hidden;
  opacity: 0;
  line-height: 1;
  user-select: text;
  -webkit-user-select: text;
}
.text-layer ::selection { background: rgba(59,130,246,0.5); color: transparent; }
:deep(.text-layer > span) {
  color: transparent;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
}

/* ── Lens selection box ── */
.lens-overlay-box {
  position: absolute;
  display: none;
  border: 2px solid #4285f4;
  background: rgba(66,133,244,0.1);
  pointer-events: none;
  z-index: 100;
}

/* ── Lens result panel ── */
.lens-result-panel {
  position: fixed;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.3);
  z-index: 5000;
  width: 360px;
  max-width: 95vw;
  overflow: hidden;
}
.lr-header {
  background: #1a365d;
  color: white;
  padding: 10px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
}
.lr-header button { background: none; border: none; color: white; cursor: pointer; font-size: 16px; }
.lr-text {
  padding: 16px;
  font-size: 14px;
  color: #333;
  line-height: 1.6;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  border-bottom: 1px solid #e9ecef;
}
.lr-actions { display: flex; gap: 8px; padding: 12px 16px; flex-wrap: wrap; }
.lr-btn {
  padding: 7px 14px;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  background: white;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s;
}
.lr-btn:hover { background: #f8f9fa; }
.lr-btn.primary { background: #2c5aa0; color: white; border-color: #2c5aa0; }
.lr-btn.primary:hover { background: #1a365d; }

/* ── Menú contextual ── */
.context-menu {
  position: fixed;
  background: white;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.25);
  padding: 6px 0;
  z-index: 4000;
  min-width: 220px;
}
.cm-item {
  padding: 11px 20px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: background 0.15s;
}
.cm-item:hover { background: #f3f4f6; }
.cm-sep { height: 1px; background: #e9ecef; margin: 4px 0; }

/* ── Banner ayuda ── */
.help-banner {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  padding: 16px 24px;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  z-index: 3000;
  max-width: 340px;
  animation: slideInRight 0.5s ease-out;
}
@keyframes slideInRight { from { transform: translateX(400px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
.help-banner h4 { margin: 0 0 10px; font-size: 15px; }
.help-banner ul { padding-left: 18px; font-size: 13px; line-height: 1.7; margin: 0; }
.banner-close { position: absolute; top: 8px; right: 10px; background: rgba(255,255,255,0.2); border: none; color: white; width: 22px; height: 22px; border-radius: 50%; cursor: pointer; font-size: 14px; }

/* ── Toast ── */
.pdf-toast {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  z-index: 9999;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
  color: white;
  animation: fadeIn 0.3s ease;
}
.pdf-toast.success { background: #28a745; }
.pdf-toast.error   { background: #dc3545; }
.pdf-toast.warning { background: #ffc107; color: #333; }
.pdf-toast.info    { background: #17a2b8; }
@keyframes fadeIn { from { opacity:0; transform: translateX(-50%) translateY(-10px); } to { opacity:1; transform: translateX(-50%) translateY(0); } }

@media (max-width: 768px) {
  .pdf-toolbar { gap: 6px; padding: 8px 10px; }
  .tb-btn { padding: 6px 10px; font-size: 12px; }
  .tomo-info, .zoom-label { display: none; }
}
</style>
