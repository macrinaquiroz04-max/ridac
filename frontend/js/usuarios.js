// Gestión de usuarios

// Obtener todos los usuarios
async function getUsuarios(params = {}) {
    try {
        return await apiGet(API_ROUTES.USERS, params);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Obtener usuario por ID
async function getUsuario(id) {
    try {
        return await apiGet(API_ROUTES.USER_BY_ID(id));
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Crear usuario
async function createUsuario(data) {
    try {
        return await apiPost(API_ROUTES.USERS, data);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Actualizar usuario
async function updateUsuario(id, data) {
    try {
        return await apiPut(API_ROUTES.USER_BY_ID(id), data);
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Eliminar usuario
async function deleteUsuario(id) {
    try {
        if (!confirm('¿Estás seguro de que deseas eliminar este usuario?')) {
            return false;
        }
        await apiDelete(API_ROUTES.USER_BY_ID(id));
        showToast('Usuario eliminado correctamente', 'success');
        return true;
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Obtener permisos de un usuario
async function getUsuarioPermisos(id) {
    try {
        return await apiGet(API_ROUTES.USER_PERMISOS(id));
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Actualizar permisos de un usuario
async function updateUsuarioPermisos(id, permisos) {
    try {
        return await apiPut(API_ROUTES.USER_PERMISOS(id), { permisos });
    } catch (error) {
        handleApiError(error);
        throw error;
    }
}

// Renderizar lista de usuarios
function renderUsuarios(usuarios, container) {
    if (!usuarios || usuarios.length === 0) {
        container.innerHTML = '<p class="empty-state">No hay usuarios registrados</p>';
        return;
    }

    // Ordenar por ID ascendente por defecto
    usuarios.sort((a, b) => a.id - b.id);

    const table = document.createElement('table');
    table.className = 'data-table';
    table.innerHTML = `
        <thead>
            <tr>
                <th>ID</th>
                <th>Usuario</th>
                <th>Nombre</th>
                <th>Email</th>
                <th>Rol</th>
                <th>Estado</th>
                <th>Último Acceso</th>
                <th>Acciones</th>
            </tr>
        </thead>
        <tbody>
            ${usuarios.map(user => `
                <tr data-user-id="${user.id}">
                    <td><strong>${user.id}</strong></td>
                    <td>${escapeHtml(user.username || user.nombre)}</td>
                    <td>
                        <div class="user-cell">
                            <div class="user-avatar">${getInitials(user.nombre)}</div>
                            <span>${escapeHtml(user.nombre)}</span>
                        </div>
                    </td>
                    <td>${escapeHtml(user.email)}</td>
                    <td><span class="badge badge-${user.rol}">${capitalize(user.rol)}</span></td>
                    <td>
                        <span class="status-badge ${user.activo ? 'status-active' : 'status-inactive'}">
                            ${user.activo ? 'Activo' : 'Inactivo'}
                        </span>
                    </td>
                    <td>${formatFecha(user.ultimo_acceso)}</td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-icon btn-edit" data-action="edit" data-id="${user.id}" title="Editar">
                                ✏️
                            </button>
                            <button class="btn-icon btn-permisos" data-action="permisos" data-id="${user.id}" title="Permisos">
                                🔐
                            </button>
                            ${user.id !== getUser().id ? `
                                <button class="btn-icon btn-delete" data-action="delete" data-id="${user.id}" title="Eliminar">
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

    // Event listeners para acciones
    table.addEventListener('click', handleUsuarioAction);
}

// Manejar acciones de usuario
async function handleUsuarioAction(event) {
    const button = event.target.closest('[data-action]');
    if (!button) return;

    const action = button.dataset.action;
    const userId = parseInt(button.dataset.id);

    switch (action) {
        case 'edit':
            openEditUsuarioModal(userId);
            break;
        case 'permisos':
            openPermisosModal(userId);
            break;
        case 'delete':
            const deleted = await deleteUsuario(userId);
            if (deleted) {
                button.closest('tr').remove();
            }
            break;
    }
}

// Modal para editar usuario
function openEditUsuarioModal(userId) {
    // Implementación en la página usuarios.html
    const event = new CustomEvent('openEditUsuario', { detail: { userId } });
    document.dispatchEvent(event);
}

// Modal para permisos
function openPermisosModal(userId) {
    // Implementación en la página usuarios.html
    const event = new CustomEvent('openPermisos', { detail: { userId } });
    document.dispatchEvent(event);
}

// Filtrar usuarios
function filterUsuarios(usuarios, query) {
    if (!query) return usuarios;

    query = query.toLowerCase();
    return usuarios.filter(user =>
        user.nombre.toLowerCase().includes(query) ||
        user.email.toLowerCase().includes(query) ||
        user.rol.toLowerCase().includes(query)
    );
}

// Ordenar usuarios
function sortUsuarios(usuarios, field, order = 'asc') {
    return usuarios.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];

        if (typeof aVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }

        if (order === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
}
