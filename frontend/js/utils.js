// Utilidades generales del sistema

// Formatear fecha
function formatFecha(fecha) {
    if (!fecha) return 'N/A';
    const date = new Date(fecha);
    const dia = String(date.getDate()).padStart(2, '0');
    const mes = String(date.getMonth() + 1).padStart(2, '0');
    const anio = date.getFullYear();
    const horas = String(date.getHours()).padStart(2, '0');
    const minutos = String(date.getMinutes()).padStart(2, '0');
    return `${dia}/${mes}/${anio} ${horas}:${minutos}`;
}

// Formatear tamaño de archivo
function formatFileSize(bytes) {
    if (!bytes) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

// Mostrar toast notification
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    // Animación de entrada
    setTimeout(() => toast.classList.add('show'), 10);

    // Remover después de la duración
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Mostrar spinner de carga
function showLoading(target = null) {
    const spinner = document.createElement('div');
    spinner.className = 'spinner';
    spinner.innerHTML = '<div class="spinner-circle"></div>';

    if (target) {
        target.appendChild(spinner);
    } else {
        spinner.classList.add('spinner-overlay');
        document.body.appendChild(spinner);
    }

    return spinner;
}

// Ocultar spinner
function hideLoading(spinner) {
    if (spinner && spinner.parentNode) {
        spinner.remove();
    }
}

// Validar email
function validateEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

// Validar formulario
function validateForm(formElement) {
    const inputs = formElement.querySelectorAll('input[required], select[required], textarea[required]');
    let isValid = true;

    inputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('error');
            isValid = false;
        } else {
            input.classList.remove('error');
        }

        // Validación específica para email
        if (input.type === 'email' && input.value && !validateEmail(input.value)) {
            input.classList.add('error');
            isValid = false;
        }
    });

    return isValid;
}

// Limpiar errores de formulario
function clearFormErrors(formElement) {
    const inputs = formElement.querySelectorAll('.error');
    inputs.forEach(input => input.classList.remove('error'));
}

// Confirmar acción
function confirm(message) {
    return window.confirm(message);
}

// Escapar HTML para prevenir XSS
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

// Debounce para búsquedas
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Obtener parámetros de URL
function getUrlParams() {
    const params = {};
    const searchParams = new URLSearchParams(window.location.search);
    for (const [key, value] of searchParams) {
        params[key] = value;
    }
    return params;
}

// Redirigir a página
function redirectTo(page) {
    window.location.href = page;
}

// Copiar al portapapeles
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copiado al portapapeles', 'success');
    } catch (err) {
        showToast('Error al copiar', 'error');
    }
}

// Descargar archivo
function downloadFile(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// Generar ID único
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// Highlight texto en búsqueda
function highlightText(text, query) {
    if (!query) return escapeHtml(text);
    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return escapeHtml(text).replace(regex, '<mark>$1</mark>');
}

function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Obtener iniciales de nombre
function getInitials(nombre) {
    return nombre
        .split(' ')
        .map(word => word[0])
        .join('')
        .toUpperCase()
        .substr(0, 2);
}

// Capitalizar primera letra
function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1).toLowerCase();
}

// Pluralizar
function pluralize(count, singular, plural) {
    return count === 1 ? singular : plural;
}
