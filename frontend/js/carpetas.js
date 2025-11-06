// Gestión de carpetas y tomos

// Obtener todas las carpetas
async function getCarpetas(params = {}) {
    try {
        return await apiGet(API_ROUTES.CARPETAS, params);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Obtener carpeta por ID
async function getCarpeta(id) {
    try {
        return await apiGet(API_ROUTES.CARPETA_BY_ID(id));
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Crear carpeta
async function createCarpeta(data) {
    try {
        return await apiPost(API_ROUTES.CARPETAS, data);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Actualizar carpeta
async function updateCarpeta(id, data) {
    try {
        return await apiPut(API_ROUTES.CARPETA_BY_ID(id), data);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Eliminar carpeta
async function deleteCarpeta(id) {
    try {
        if (!confirm('¿Estás seguro de que deseas eliminar esta carpeta? Se eliminarán todos sus tomos.')) {
            return false;
        }
        await apiDelete(API_ROUTES.CARPETA_BY_ID(id));
        showToast('Carpeta eliminada correctamente', 'success');
        return true;
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Obtener tomos de una carpeta
async function getTomosCarpeta(carpetaId) {
    try {
        return await apiGet(API_ROUTES.CARPETA_TOMOS(carpetaId));
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Obtener tomo por ID
async function getTomo(id) {
    try {
        return await apiGet(API_ROUTES.TOMO_BY_ID(id));
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Crear tomo
async function createTomo(carpetaId, data) {
    try {
        return await apiPost(API_ROUTES.TOMOS, {
            ...data,
            carpeta_id: carpetaId
        });
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Actualizar tomo
async function updateTomo(id, data) {
    try {
        return await apiPut(API_ROUTES.TOMO_BY_ID(id), data);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Eliminar tomo
async function deleteTomo(id) {
    try {
        if (!confirm('¿Estás seguro de que deseas eliminar este tomo?')) {
            return false;
        }
        await apiDelete(API_ROUTES.TOMO_BY_ID(id));
        showToast('Tomo eliminado correctamente', 'success');
        return true;
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Subir PDF a tomo
async function uploadTomoFile(tomoId, file, onProgress = null) {
    try {
        const formData = new FormData();
        formData.append('file', file);

        const xhr = new XMLHttpRequest();

        return new Promise((resolve, reject) => {
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable && onProgress) {
                    const percentComplete = (e.loaded / e.total) * 100;
                    onProgress(percentComplete);
                }
            });

            xhr.addEventListener('load', () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(JSON.parse(xhr.responseText));
                } else {
                    reject(new Error(`Error ${xhr.status}: ${xhr.statusText}`));
                }
            });

            xhr.addEventListener('error', () => {
                reject(new Error('Error de red al subir el archivo'));
            });

            const token = getToken();
            xhr.open('POST', API_URL + API_ROUTES.TOMO_UPLOAD(tomoId));
            if (token) {
                xhr.setRequestHeader('Authorization', `Bearer ${token}`);
            }
            xhr.send(formData);
        });
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Descargar PDF de tomo
async function downloadTomo(tomoId, filename) {
    try {
        await apiDownload(API_ROUTES.TOMO_DOWNLOAD(tomoId), filename);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Renderizar carpetas
function renderCarpetas(carpetas, container) {
    if (!carpetas || carpetas.length === 0) {
        container.innerHTML = '<p class="empty-state">No hay carpetas registradas</p>';
        return;
    }

    const grid = document.createElement('div');
    grid.className = 'carpetas-grid';

    carpetas.forEach(carpeta => {
        const card = document.createElement('div');
        card.className = 'carpeta-card';
        card.innerHTML = `
            <div class="carpeta-icon">📁</div>
            <div class="carpeta-info">
                <h3>${escapeHtml(carpeta.numero_carpeta)}</h3>
                <p>${escapeHtml(carpeta.nombre || 'Sin nombre')}</p>
                <div class="carpeta-meta">
                    <span>${carpeta.total_tomos || 0} ${pluralize(carpeta.total_tomos || 0, 'tomo', 'tomos')}</span>
                    <span>${formatFecha(carpeta.fecha_creacion)}</span>
                </div>
            </div>
            <div class="carpeta-actions">
                <button class="btn-icon" data-action="view" data-id="${carpeta.id}" title="Ver tomos">
                    👁️
                </button>
                ${hasPermission(PERMISOS.EDITAR_CARPETAS) ? `
                    <button class="btn-icon" data-action="edit" data-id="${carpeta.id}" title="Editar">
                        ✏️
                    </button>
                ` : ''}
                ${hasPermission(PERMISOS.ELIMINAR_CARPETAS) ? `
                    <button class="btn-icon btn-delete" data-action="delete" data-id="${carpeta.id}" title="Eliminar">
                        🗑️
                    </button>
                ` : ''}
            </div>
        `;

        grid.appendChild(card);
    });

    container.innerHTML = '';
    container.appendChild(grid);

    // Event listeners
    grid.addEventListener('click', handleCarpetaAction);
}

// Renderizar tomos
function renderTomos(tomos, container) {
    if (!tomos || tomos.length === 0) {
        container.innerHTML = '<p class="empty-state">No hay tomos en esta carpeta</p>';
        return;
    }

    const table = document.createElement('table');
    table.className = 'data-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>Número</th>
                <th>Nombre</th>
                <th>Archivo</th>
                <th>Estado OCR</th>
                <th>Tamaño</th>
                <th>Fecha</th>
                <th>Acciones</th>
            </tr>
        </thead>
        <tbody>
            ${tomos.map(tomo => `
                <tr data-tomo-id="${tomo.id}">
                    <td><strong>${escapeHtml(tomo.numero_tomo)}</strong></td>
                    <td>${escapeHtml(tomo.nombre || 'Sin nombre')}</td>
                    <td>
                        ${tomo.ruta_pdf ? `
                            <span class="file-indicator">📄 PDF</span>
                        ` : `
                            <span class="file-indicator-empty">Sin archivo</span>
                        `}
                    </td>
                    <td>
                        <span class="status-badge ${getOcrStatusClass(tomo.estado_ocr)}">
                            ${getOcrStatusText(tomo.estado_ocr)}
                        </span>
                    </td>
                    <td>${formatFileSize(tomo.tamano_archivo)}</td>
                    <td>${formatFecha(tomo.fecha_creacion)}</td>
                    <td>
                        <div class="action-buttons">
                            ${tomo.ruta_pdf ? `
                                <button class="btn-icon" data-action="view" data-id="${tomo.id}" title="Ver PDF">
                                    👁️
                                </button>
                                <button class="btn-icon" data-action="download" data-id="${tomo.id}" title="Descargar">
                                    ⬇️
                                </button>
                            ` : hasPermission(PERMISOS.SUBIR_DOCUMENTOS) ? `
                                <button class="btn-icon" data-action="upload" data-id="${tomo.id}" title="Subir PDF">
                                    ⬆️
                                </button>
                            ` : ''}
                            ${hasPermission(PERMISOS.EDITAR_CARPETAS) ? `
                                <button class="btn-icon" data-action="edit" data-id="${tomo.id}" title="Editar">
                                    ✏️
                                </button>
                            ` : ''}
                            ${hasPermission(PERMISOS.ELIMINAR_DOCUMENTOS) ? `
                                <button class="btn-icon btn-delete" data-action="delete" data-id="${tomo.id}" title="Eliminar">
                                    🗑️
                                </button>
                            ` : ''}
                        </div>
                    </td>
                </tr>
            `).join('')}
        </tbody>
    `;

    container.innerHTML = '';
    container.appendChild(table);

    // Event listeners
    table.addEventListener('click', handleTomoAction);
}

// Manejar acciones de carpeta
async function handleCarpetaAction(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;

    const action = button.dataset.action;
    const carpetaId = parseInt(button.dataset.id);

    switch (action) {
        case 'view':
            redirectTo(`carpetas.html?id=${carpetaId}`);
            break;
        case 'edit':
            const event = new CustomEvent('openEditCarpeta', { detail: { carpetaId } });
            document.dispatchEvent(event);
            break;
        case 'delete':
            const deleted = await deleteCarpeta(carpetaId);
            if (deleted) {
                button.closest('.carpeta-card').remove();
            }
            break;
    }
}

// Manejar acciones de tomo
async function handleTomoAction(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;

    const action = button.dataset.action;
    const tomoId = parseInt(button.dataset.id);

    switch (action) {
        case 'view':
            redirectTo(`visor.html?tomo=${tomoId}`);
            break;
        case 'download':
            const tomo = await getTomo(tomoId);
            await downloadTomo(tomoId, `${tomo.numero_tomo}.pdf`);
            break;
        case 'upload':
            const uploadEvent = new CustomEvent('openUploadTomo', { detail: { tomoId } });
            document.dispatchEvent(uploadEvent);
            break;
        case 'edit':
            const editEvent = new CustomEvent('openEditTomo', { detail: { tomoId } });
            document.dispatchEvent(editEvent);
            break;
        case 'delete':
            const deleted = await deleteTomo(tomoId);
            if (deleted) {
                button.closest('tr').remove();
            }
            break;
    }
}

// Estado OCR helpers
function getOcrStatusClass(estado) {
    const statusMap = {
        'pendiente': 'status-pending',
        'procesando': 'status-processing',
        'completado': 'status-completed',
        'error': 'status-error'
    };
    return statusMap[estado] || 'status-pending';
}

function getOcrStatusText(estado) {
    const textMap = {
        'pendiente': 'Pendiente',
        'procesando': 'Procesando',
        'completado': 'Completado',
        'error': 'Error'
    };
    return textMap[estado] || estado;
}
