// Funciones para interactuar con la API

// Obtener token del localStorage
function getToken() {
    return localStorage.getItem(APP_CONFIG.TOKEN_KEY);
}

// Guardar token en localStorage
function saveToken(token) {
    localStorage.setItem(APP_CONFIG.TOKEN_KEY, token);
}

// Eliminar token
function removeToken() {
    localStorage.removeItem(APP_CONFIG.TOKEN_KEY);
}

// Headers para peticiones
function getHeaders(includeAuth = true, isJson = true) {
    const headers = {};

    if (isJson) {
        headers['Content-Type'] = 'application/json';
    }

    if (includeAuth) {
        const token = getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
    }

    return headers;
}

// Manejar respuesta de la API
async function handleResponse(response) {
    const contentType = response.headers.get('content-type');

    // Si es un blob (archivo)
    if (contentType && contentType.includes('application/pdf')) {
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        return await response.blob();
    }

    // Si es JSON
    if (contentType && contentType.includes('application/json')) {
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || data.message || `Error ${response.status}`);
        }

        return data;
    }

    // Respuesta de texto
    const text = await response.text();
    if (!response.ok) {
        throw new Error(text || `Error ${response.status}`);
    }

    return text;
}

// GET request
async function apiGet(endpoint, params = {}) {
    try {
        const url = new URL(API_URL + endpoint);
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });

        const response = await fetch(url.toString(), {
            method: 'GET',
            headers: getHeaders()
        });

        return await handleResponse(response);
    } catch (error) {
        console.error('API GET Error:', error);
        throw error;
    }
}

// POST request
async function apiPost(endpoint, data = {}) {
    try {
        const response = await fetch(API_URL + endpoint, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });

        return await handleResponse(response);
    } catch (error) {
        console.error('API POST Error:', error);
        throw error;
    }
}

// PUT request
async function apiPut(endpoint, data = {}) {
    try {
        const response = await fetch(API_URL + endpoint, {
            method: 'PUT',
            headers: getHeaders(),
            body: JSON.stringify(data)
        });

        return await handleResponse(response);
    } catch (error) {
        console.error('API PUT Error:', error);
        throw error;
    }
}

// DELETE request
async function apiDelete(endpoint) {
    try {
        const response = await fetch(API_URL + endpoint, {
            method: 'DELETE',
            headers: getHeaders()
        });

        return await handleResponse(response);
    } catch (error) {
        console.error('API DELETE Error:', error);
        throw error;
    }
}

// POST con FormData (para archivos)
async function apiPostFormData(endpoint, formData) {
    try {
        const headers = {};
        const token = getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(API_URL + endpoint, {
            method: 'POST',
            headers: headers,
            body: formData
        });

        return await handleResponse(response);
    } catch (error) {
        console.error('API POST FormData Error:', error);
        throw error;
    }
}

// Descargar archivo
async function apiDownload(endpoint, filename) {
    try {
        const response = await fetch(API_URL + endpoint, {
            method: 'GET',
            headers: getHeaders()
        });

        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }

        const blob = await response.blob();
        downloadFile(blob, filename);
    } catch (error) {
        console.error('API Download Error:', error);
        throw error;
    }
}

// Verificar si hay error de autenticación
function isAuthError(error) {
    return error.message.includes('401') ||
           error.message.includes('token') ||
           error.message.includes('autenticación') ||
           error.message.includes('no autorizado');
}

// Manejar error global
function handleApiError(error) {
    if (isAuthError(error)) {
        showToast('Sesión expirada. Por favor inicia sesión nuevamente.', 'error');
        setTimeout(() => {
            logout();
        }, 1500);
    } else {
        showToast(error.message || 'Error en la operación', 'error');
    }
}

// Objeto API principal para usar en los HTML
const api = {
    get: async (endpoint) => {
        return await apiGet(endpoint);
    },
    post: async (endpoint, data) => {
        return await apiPost(endpoint, data);
    },
    put: async (endpoint, data) => {
        return await apiPut(endpoint, data);
    },
    delete: async (endpoint) => {
        return await apiDelete(endpoint);
    },
    postFormData: async (endpoint, formData) => {
        return await apiPostFormData(endpoint, formData);
    },
    download: async (endpoint, filename) => {
        return await apiDownload(endpoint, filename);
    }
};
