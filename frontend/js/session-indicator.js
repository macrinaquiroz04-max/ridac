/**
 * 🔐 Indicador de Estado de Sesión
 * Muestra visualmente el estado de autenticación y tiempo de inactividad
 */

class SessionIndicator {
    constructor() {
        this.createIndicator();
        this.updateInterval = null;
        this.authManager = window.authManager;
    }

    createIndicator() {
        // Crear HTML del indicador
        const indicator = document.createElement('div');
        indicator.id = 'session-indicator';
        indicator.innerHTML = `
            <style>
                #session-indicator {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: rgba(26, 54, 93, 0.95);
                    color: white;
                    padding: 12px 20px;
                    border-radius: 25px;
                    font-size: 12px;
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
                    z-index: 9999;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    transition: all 0.3s ease;
                    cursor: pointer;
                    user-select: none;
                }
                
                #session-indicator:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
                }
                
                #session-indicator.active {
                    background: rgba(56, 161, 105, 0.95);
                }
                
                #session-indicator.warning {
                    background: rgba(214, 158, 46, 0.95);
                    animation: pulse 2s infinite;
                }
                
                #session-indicator.inactive {
                    background: rgba(229, 62, 62, 0.95);
                    animation: pulse 1s infinite;
                }
                
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.7; }
                }
                
                .session-status-icon {
                    font-size: 16px;
                }
                
                .session-status-text {
                    font-weight: 500;
                }
                
                .session-time {
                    font-size: 11px;
                    opacity: 0.9;
                }
                
                #session-indicator.minimized {
                    padding: 10px;
                    border-radius: 50%;
                    width: 45px;
                    height: 45px;
                    justify-content: center;
                }
                
                #session-indicator.minimized .session-status-text,
                #session-indicator.minimized .session-time {
                    display: none;
                }
            </style>
            <span class="session-status-icon">🔐</span>
            <div style="display: flex; flex-direction: column; gap: 2px;">
                <span class="session-status-text">Sesión activa</span>
                <span class="session-time">Inactividad: 0s</span>
            </div>
        `;

        document.body.appendChild(indicator);

        // Click para minimizar/maximizar
        indicator.addEventListener('click', () => {
            indicator.classList.toggle('minimized');
        });

        this.indicator = indicator;
        this.startUpdating();
    }

    startUpdating() {
        // Actualizar cada segundo
        this.updateInterval = setInterval(() => {
            this.updateStatus();
        }, 1000);
    }

    updateStatus() {
        if (!this.authManager) {
            this.authManager = window.authManager;
            if (!this.authManager) return;
        }

        const inactiveSeconds = this.authManager.getInactivityTimeRemaining();
        const maxInactivity = this.authManager.INACTIVITY_TIMEOUT / 1000;
        const inactivePercent = 1 - (inactiveSeconds / maxInactivity);

        const icon = this.indicator.querySelector('.session-status-icon');
        const text = this.indicator.querySelector('.session-status-text');
        const time = this.indicator.querySelector('.session-time');

        // Actualizar según nivel de inactividad
        if (inactivePercent < 0.5) {
            // Sesión activa (< 50% del tiempo de inactividad)
            this.indicator.className = 'active';
            icon.textContent = '✅';
            text.textContent = 'Sesión activa';
        } else if (inactivePercent < 0.8) {
            // Advertencia (50-80% del tiempo)
            this.indicator.className = 'warning';
            icon.textContent = '⚠️';
            text.textContent = 'Inactividad detectada';
        } else {
            // Peligro (> 80% del tiempo)
            this.indicator.className = 'inactive';
            icon.textContent = '⏰';
            text.textContent = '¡Sesión por expirar!';
        }

        // Formatear tiempo restante
        const minutes = Math.floor(inactiveSeconds / 60);
        const seconds = inactiveSeconds % 60;
        time.textContent = `Tiempo restante: ${minutes}m ${seconds}s`;
    }

    destroy() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        if (this.indicator) {
            this.indicator.remove();
        }
    }
}

// Auto-inicializar si hay sesión activa
let sessionIndicator = null;

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    
    // Solo mostrar en páginas con sesión activa (no en login)
    // Y solo si está habilitado explícitamente
    if (token && window.ENABLE_SESSION_INDICATOR && 
        !window.location.pathname.includes('index.html') && 
        window.location.pathname !== '/') {
        // Esperar a que AuthManager esté listo
        setTimeout(() => {
            if (window.authManager) {
                sessionIndicator = new SessionIndicator();
                window.sessionIndicator = sessionIndicator;
            }
        }, 100);
    }
});

// Limpiar al salir
window.addEventListener('beforeunload', () => {
    if (sessionIndicator) {
        sessionIndicator.destroy();
    }
});
