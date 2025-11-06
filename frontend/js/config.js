// Configuración optimizada para Sistema OCR FGJCDMX
// Desarrollado por: Eduardo Lozada Quiroz, ISC
// Cliente: Unidad de Análisis y Contexto (UAyC)
// Hash de verificación: ELQ_ISC_UAYC_OCT2025
// Prioriza fgj-ocr.local como dominio principal
const isNginx = window.location.port === '' || window.location.port === '80' || window.location.port === '443';
const isFGJDomain = window.location.hostname === 'fgj-ocr.local';

// Determinar URL de la API basada en el contexto
let API_URL;
if (isFGJDomain || window.location.hostname === '172.22.134.61') {
    // Usar configuración optimizada para dominio FGJ
    API_URL = `${window.location.protocol}//${window.location.hostname}/api`;
} else if (isNginx) {
    // Modo nginx proxy genérico
    API_URL = `${window.location.protocol}//${window.location.hostname}/api`;
} else {
    // Backend directo (desarrollo)
    API_URL = `${window.location.protocol}//${window.location.hostname}:${window.location.port}/api`;
}

// Configuración de la aplicación
const APP_CONFIG = {
    TOKEN_KEY: 'token',
    USER_KEY: 'usuario',
    TOKEN_REFRESH_INTERVAL: 14 * 60 * 1000, // 14 minutos (antes de expirar)
    SESSION_CHECK_INTERVAL: 60 * 1000, // Verificar sesión cada minuto
    SECURE_MODE: true // Modo seguro activado
};

console.log('╔══════════════════════════════════════════════════════╗');
console.log('║   �️  SISTEMA OCR FGJCDMX - CONFIG INICIADO          ║');
console.log('╚══════════════════════════════════════════════════════╝');
console.log('🌍 Ubicación actual:', window.location.href);
console.log('🔌 Puerto detectado:', window.location.port || '80/443 (default)');
console.log('🏛️ Dominio FGJ:', isFGJDomain ? 'SÍ (fgj-ocr.local)' : 'NO');
console.log('🔧 Modo detectado:', isNginx ? 'NGINX PROXY' : 'BACKEND DIRECTO');
console.log('🔗 API URL configurada:', API_URL);
console.log('🔒 Modo seguro:', APP_CONFIG.SECURE_MODE ? 'ACTIVADO' : 'DESACTIVADO');
console.log('══════════════════════════════════════════════════════');

