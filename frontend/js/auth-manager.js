/**
 * 🔐 Sistema de Gestión de Autenticación
 * - Renovación automática de tokens
 * - Detección de inactividad
 * - Cierre de sesión automático
 */

class AuthManager {
    constructor() {
        // Detectar API_URL: usar variable global o construir desde location
        if (window.API_URL) {
            this.API_URL = window.API_URL;
        } else if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            this.API_URL = 'http://localhost:8000/api';
        } else {
            // En producción, usar la URL actual con /api
            this.API_URL = `${window.location.origin}/api`;
        }
        
        // Configuración de tiempos (en milisegundos)
        this.TOKEN_REFRESH_INTERVAL = 14 * 60 * 1000; // 14 minutos (token expira en 15)
        this.INACTIVITY_TIMEOUT = 30 * 60 * 1000;     // 30 minutos de inactividad
        this.CHECK_INTERVAL = 60 * 1000;              // Verificar cada 1 minuto
        
        // Estado interno
        this.refreshTimer = null;
        this.inactivityTimer = null;
        this.checkTimer = null;
        this.lastActivity = Date.now();
        
        // Eventos que resetean el contador de inactividad
        this.activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
        
        this.init();
    }

    init() {
        const token = localStorage.getItem('token');
        if (!token) {
            return; // No hay sesión activa
        }

        console.log('🔐 AuthManager: Monitoreo de sesión activo');
        console.log(`⏱️ Configuración: Token check cada ${this.TOKEN_REFRESH_INTERVAL/60000}min, Inactividad máx ${this.INACTIVITY_TIMEOUT/60000}min`);
        
        // Iniciar renovación automática de tokens
        this.startTokenRefresh();
        
        // Iniciar detección de inactividad
        this.startInactivityDetection();
        
        // Iniciar verificación periódica
        this.startPeriodicCheck();
    }

    /**
     * 🔄 Renovación automática de tokens
     */
    startTokenRefresh() {
        // Verificar token inmediatamente
        this.checkAndRefreshToken();
        
        // Configurar renovación periódica
        this.refreshTimer = setInterval(() => {
            this.checkAndRefreshToken();
        }, this.TOKEN_REFRESH_INTERVAL);
    }

    async checkAndRefreshToken() {
        const token = localStorage.getItem('token');
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!token) {
            this.cleanup();
            return;
        }

        try {
            // Método 1: Si tenemos refresh token, usarlo
            if (refreshToken) {
                try {
                    const response = await fetch(`${this.API_URL}/auth/refresh`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({ refresh_token: refreshToken })
                    });

                    if (response.ok) {
                        const data = await response.json();
                        
                        // Guardar nuevo token
                        if (data.access_token) {
                            localStorage.setItem('token', data.access_token);
                            console.log('✅ Token renovado exitosamente');
                            return;
                        }
                    } else if (response.status === 404) {
                        // Endpoint no disponible, continuar con verificación simple
                        console.debug('ℹ️ Endpoint /auth/refresh no disponible');
                    }
                } catch (err) {
                    console.debug('ℹ️ No se pudo renovar token, verificando validez...');
                }
            }
            
            // Método 2: Verificar si el token actual sigue válido
            const verifyResponse = await fetch(`${this.API_URL}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (verifyResponse.ok) {
                console.debug('✅ Sesión válida');
                // Token válido, actualizar tiempo de actividad
                this.lastActivity = Date.now();
            } else if (verifyResponse.status === 401) {
                // Token expirado o inválido
                console.warn('⚠️ Token expirado, cerrando sesión...');
                this.logout('Su sesión ha expirado. Por favor, inicie sesión nuevamente.');
            } else if (verifyResponse.status === 404) {
                console.warn('⚠️ API no disponible. URL:', this.API_URL);
            }
        } catch (error) {
            // Errores de red - no hacer nada, intentar en el próximo ciclo
            console.debug('⚠️ Error de red al verificar sesión (se reintentará)');
        }
    }

    /**
     * ⏰ Detección de inactividad
     */
    startInactivityDetection() {
        // Registrar actividad del usuario
        this.activityEvents.forEach(event => {
            document.addEventListener(event, () => this.resetInactivityTimer(), true);
        });

        // Iniciar timer de inactividad
        this.resetInactivityTimer();
    }

    resetInactivityTimer() {
        this.lastActivity = Date.now();
        
        // Limpiar timer anterior
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
        }
        
        // Configurar nuevo timer
        this.inactivityTimer = setTimeout(() => {
            this.logout('Su sesión ha sido cerrada por inactividad.');
        }, this.INACTIVITY_TIMEOUT);
    }

    /**
     * 🔍 Verificación periódica del estado de la sesión
     */
    startPeriodicCheck() {
        this.checkTimer = setInterval(async () => {
            await this.verifySession();
        }, this.CHECK_INTERVAL);
    }

    async verifySession() {
        const token = localStorage.getItem('token');
        if (!token) {
            this.cleanup();
            return;
        }

        try {
            const response = await fetch(`${this.API_URL}/auth/me`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                console.warn('⚠️ Sesión inválida detectada');
                this.logout('Su sesión ya no es válida. Por favor, inicie sesión nuevamente.');
            }
        } catch (error) {
            // Error de red, no hacer nada
            console.debug('Error verificando sesión:', error.message);
        }
    }

    /**
     * 🚪 Cerrar sesión
     */
    logout(message = null) {
        console.log('🚪 Cerrando sesión...');
        
        // Limpiar storage
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        sessionStorage.clear();
        
        // Limpiar timers
        this.cleanup();
        
        // Mostrar mensaje si se proporciona
        if (message) {
            alert(`⚠️ ${message}`);
        }
        
        // Redirigir al login
        window.location.href = 'index.html';
    }

    /**
     * 🧹 Limpiar recursos
     */
    cleanup() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
        
        if (this.inactivityTimer) {
            clearTimeout(this.inactivityTimer);
            this.inactivityTimer = null;
        }
        
        if (this.checkTimer) {
            clearInterval(this.checkTimer);
            this.checkTimer = null;
        }
        
        console.log('🧹 AuthManager limpiado');
    }

    /**
     * 📊 Obtener tiempo restante de inactividad
     */
    getInactivityTimeRemaining() {
        const elapsed = Date.now() - this.lastActivity;
        const remaining = Math.max(0, this.INACTIVITY_TIMEOUT - elapsed);
        return Math.floor(remaining / 1000); // Retornar en segundos
    }

    /**
     * 🔄 Forzar renovación manual del token
     */
    async forceRefresh() {
        await this.checkAndRefreshToken();
    }
}

// 🚀 Auto-inicializar cuando el DOM esté listo
let authManager = null;

document.addEventListener('DOMContentLoaded', () => {
    // Solo inicializar si hay token (usuario logueado)
    const token = localStorage.getItem('token');
    if (token && !window.location.pathname.includes('index.html') && window.location.pathname !== '/') {
        authManager = new AuthManager();
        
        // Exponer globalmente para debugging
        window.authManager = authManager;
    }
});

// Limpiar al salir de la página
window.addEventListener('beforeunload', () => {
    if (authManager) {
        authManager.cleanup();
    }
});
