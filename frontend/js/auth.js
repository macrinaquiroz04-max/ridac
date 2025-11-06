// Gestión de autenticación

let refreshTokenInterval = null;

// Login
async function login(email, password) {
    try {
        const data = await apiPost(API_ROUTES.LOGIN, { email, password });

        if (data.access_token) {
            saveToken(data.access_token);
            saveUser(data.user);
            startTokenRefresh();
            
            // Verificar si requiere cambio de contraseña
            if (data.user.requiere_cambio_password) {
                redirectTo('cambiar-password.html');
                return data;
            }
            
            return data;
        }

        throw new Error('No se recibió token de acceso');
    } catch (error) {
        throw error;
    }
}

// Logout
function logout() {
    removeToken();
    removeUser();
    stopTokenRefresh();
    
    // Limpiar completamente la sesión
    sessionStorage.clear();
    
    // Redirigir a login
    redirectTo('index');
}

// Guardar usuario
function saveUser(user) {
    localStorage.setItem(APP_CONFIG.USER_KEY, JSON.stringify(user));
}

// Obtener usuario
function getUser() {
    const userStr = localStorage.getItem(APP_CONFIG.USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
}

// Eliminar usuario
function removeUser() {
    localStorage.removeItem(APP_CONFIG.USER_KEY);
}

// Verificar si está autenticado
function isAuthenticated() {
    return !!getToken() && !!getUser();
}

// Verificar rol
function hasRole(role) {
    const user = getUser();
    return user && user.rol === role;
}

// Verificar permiso
function hasPermission(permiso) {
    const user = getUser();
    if (!user || !user.permisos) return false;
    return user.permisos.includes(permiso);
}

// Verificar múltiples permisos (AND)
function hasAllPermissions(...permisos) {
    return permisos.every(p => hasPermission(p));
}

// Verificar algún permiso (OR)
function hasAnyPermission(...permisos) {
    return permisos.some(p => hasPermission(p));
}

// Redirigir según rol (con URLs limpias)
function redirectByRole() {
    const user = getUser();
    if (!user) {
        redirectTo('index');
        return;
    }

    switch (user.rol) {
        case 'admin':
            redirectTo('dashboard');
            break;
        case 'Director':
        case 'Subdirector':
        case 'Analista':
            redirectTo('dashboard-usuario');
            break;
        default:
            redirectTo('dashboard-usuario');
    }
}

// Función auxiliar para redirección (con URLs limpias)
function redirectTo(url) {
    // Quitar .html si está presente
    const cleanUrl = url.replace('.html', '');
    window.location.href = cleanUrl;
}

// Refrescar token
async function refreshToken() {
    try {
        const data = await apiPost(API_ROUTES.REFRESH);

        if (data.access_token) {
            saveToken(data.access_token);
            if (data.user) {
                saveUser(data.user);
            }
            return true;
        }

        return false;
    } catch (error) {
        console.error('Error al refrescar token:', error);
        logout();
        return false;
    }
}

// Iniciar refresco automático de token
function startTokenRefresh() {
    stopTokenRefresh();

    refreshTokenInterval = setInterval(async () => {
        await refreshToken();
    }, APP_CONFIG.TOKEN_REFRESH_INTERVAL);
}

// Detener refresco automático
function stopTokenRefresh() {
    if (refreshTokenInterval) {
        clearInterval(refreshTokenInterval);
        refreshTokenInterval = null;
    }
}

// Solicitar reset de contraseña
async function requestPasswordReset(email) {
    try {
        await apiPost(API_ROUTES.RESET_REQUEST, { email });
        return true;
    } catch (error) {
        throw error;
    }
}

// Confirmar reset de contraseña
async function confirmPasswordReset(token, newPassword) {
    try {
        await apiPost(API_ROUTES.RESET_CONFIRM, {
            token,
            new_password: newPassword
        });
        return true;
    } catch (error) {
        throw error;
    }
}

// Proteger página (verificar autenticación)
function protectPage() {
    if (!isAuthenticated()) {
        console.warn('🚫 Usuario no autenticado - redirigiendo a login');
        redirectTo('index');
        return false;
    }
    
    // Modo seguro: verificar que no esté en página de login
    if (APP_CONFIG.SECURE_MODE && window.location.pathname === '/index') {
        redirectByRole();
        return false;
    }
    
    return true;
}

// Proteger página con rol específico
function protectPageWithRole(allowedRoles) {
    if (!protectPage()) return false;

    const user = getUser();
    if (!allowedRoles.includes(user.rol)) {
        showToast('No tienes permisos para acceder a esta página', 'error');
        redirectTo('dashboard.html');
        return false;
    }

    return true;
}

// Proteger página con permiso específico
function protectPageWithPermission(requiredPermission) {
    if (!protectPage()) return false;

    if (!hasPermission(requiredPermission)) {
        showToast('No tienes permisos para acceder a esta página', 'error');
        redirectTo('dashboard.html');
        return false;
    }

    return true;
}

// Inicializar autenticación en páginas protegidas
function initAuth() {
    if (isAuthenticated()) {
        startTokenRefresh();
        return true;
    }
    return false;
}

// Verificar autenticación (alias de protectPage)
function verificarAuth() {
    return protectPage();
}
