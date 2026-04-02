/**
 * RIDAC Security Guard
 * - Advertencia en consola (igual que Facebook/Twitter)
 * - Bloqueo de atajos de DevTools en producción
 * - Detección básica de DevTools abiertos
 */

export function initSecurityGuard() {
  if (typeof window === 'undefined') return

  // --- Advertencia en consola (siempre activa) ---
  const STOP_STYLE = 'color:#c0392b;font-size:28px;font-weight:900;text-shadow:0 1px 2px rgba(0,0,0,.3);'
  const WARN_STYLE = 'color:#333;font-size:14px;line-height:1.6;'
  /* eslint-disable no-console */
  console.log('%c⛔ ALTO — ZONA RESTRINGIDA', STOP_STYLE)
  console.log(
    '%cEsta es una herramienta para desarrolladores.\n' +
    'Si alguien te pidió pegar código aquí, es un intento de robar tus credenciales o los datos del sistema.\n' +
    'Cierra esta ventana inmediatamente y reporta el incidente al administrador.',
    WARN_STYLE
  )
  /* eslint-enable no-console */

  // Solo en producción: bloqueos adicionales
  if (!import.meta.env.PROD) return

  // --- Bloquear atajos de DevTools ---
  document.addEventListener('keydown', (e) => {
    const ctrl = e.ctrlKey || e.metaKey

    if (
      e.key === 'F12' ||
      (ctrl && e.shiftKey && ['I', 'J', 'C', 'K'].includes(e.key.toUpperCase())) ||
      (ctrl && e.key === 'U') // ver fuente
    ) {
      e.preventDefault()
      e.stopPropagation()
      return false
    }
  }, { capture: true })

  // --- Bloquear clic derecho ---
  document.addEventListener('contextmenu', (e) => {
    e.preventDefault()
    return false
  })

  // --- Detección de DevTools abiertos (técnica de redimensionamiento) ---
  const threshold = 160
  let devToolsOpen = false

  const checkDevTools = () => {
    const widthDiff = window.outerWidth - window.innerWidth
    const heightDiff = window.outerHeight - window.innerHeight
    const isOpen = widthDiff > threshold || heightDiff > threshold
    if (isOpen && !devToolsOpen) {
      devToolsOpen = true
      // Limpiar consola y re-mostrar advertencia
      /* eslint-disable no-console */
      console.clear()
      console.log('%c⛔ ALTO — ZONA RESTRINGIDA', 'color:#c0392b;font-size:28px;font-weight:900;')
      console.log('%cActividad sospechosa detectada. Todo acceso queda registrado.', 'color:#333;font-size:13px;')
      /* eslint-enable no-console */
    }
    if (!isOpen) devToolsOpen = false
  }

  // Revisar cada 2 segundos (no impacta rendimiento)
  setInterval(checkDevTools, 2000)
  window.addEventListener('resize', checkDevTools)
}
