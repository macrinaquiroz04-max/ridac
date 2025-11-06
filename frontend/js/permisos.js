// Gestión de permisos

// Definición de permisos por categoría
const PERMISOS_CATEGORIAS = {
    usuarios: {
        nombre: 'Usuarios',
        permisos: [
            { id: PERMISOS.VER_USUARIOS, nombre: 'Ver usuarios' },
            { id: PERMISOS.CREAR_USUARIOS, nombre: 'Crear usuarios' },
            { id: PERMISOS.EDITAR_USUARIOS, nombre: 'Editar usuarios' },
            { id: PERMISOS.ELIMINAR_USUARIOS, nombre: 'Eliminar usuarios' }
        ]
    },
    carpetas: {
        nombre: 'Carpetas',
        permisos: [
            { id: PERMISOS.VER_CARPETAS, nombre: 'Ver carpetas' },
            { id: PERMISOS.CREAR_CARPETAS, nombre: 'Crear carpetas' },
            { id: PERMISOS.EDITAR_CARPETAS, nombre: 'Editar carpetas' },
            { id: PERMISOS.ELIMINAR_CARPETAS, nombre: 'Eliminar carpetas' }
        ]
    },
    documentos: {
        nombre: 'Documentos',
        permisos: [
            { id: PERMISOS.VER_DOCUMENTOS, nombre: 'Ver documentos' },
            { id: PERMISOS.SUBIR_DOCUMENTOS, nombre: 'Subir documentos' },
            { id: PERMISOS.ELIMINAR_DOCUMENTOS, nombre: 'Eliminar documentos' }
        ]
    },
    busqueda: {
        nombre: 'Búsqueda',
        permisos: [
            { id: PERMISOS.BUSCAR_OCR, nombre: 'Búsqueda OCR' }
        ]
    }
};

// Permisos por rol
const PERMISOS_POR_ROL = {
    [ROLES.ADMIN]: Object.values(PERMISOS),
    [ROLES.DIRECTOR]: [
        PERMISOS.VER_USUARIOS,
        PERMISOS.VER_CARPETAS,
        PERMISOS.CREAR_CARPETAS,
        PERMISOS.EDITAR_CARPETAS,
        PERMISOS.VER_DOCUMENTOS,
        PERMISOS.SUBIR_DOCUMENTOS,
        PERMISOS.BUSCAR_OCR
    ],
        [ROLES.SUBDIRECTOR]: [
        PERMISOS.VER_CARPETAS,
        PERMISOS.CREAR_CARPETAS,
        PERMISOS.VER_DOCUMENTOS,
        PERMISOS.SUBIR_DOCUMENTOS,
        PERMISOS.BUSCAR_OCR
    ],
    [ROLES.ANALISTA]: [
        PERMISOS.VER_CARPETAS,
        PERMISOS.VER_DOCUMENTOS,
        PERMISOS.BUSCAR_OCR
    ]
};

// Renderizar selector de permisos
function renderPermisos(container, permisosActuales = [], readonly = false) {
    container.innerHTML = '';

    Object.entries(PERMISOS_CATEGORIAS).forEach(([key, categoria]) => {
        const section = document.createElement('div');
        section.className = 'permisos-section';

        const header = document.createElement('h4');
        header.textContent = categoria.nombre;
        section.appendChild(header);

        const list = document.createElement('div');
        list.className = 'permisos-list';

        categoria.permisos.forEach(permiso => {
            const item = document.createElement('label');
            item.className = 'permiso-item';

            const checkbox = document.createElement('input');
            checkbox.type = 'checkbox';
            checkbox.value = permiso.id;
            checkbox.checked = permisosActuales.includes(permiso.id);
            checkbox.disabled = readonly;

            const label = document.createElement('span');
            label.textContent = permiso.nombre;

            item.appendChild(checkbox);
            item.appendChild(label);
            list.appendChild(item);
        });

        section.appendChild(list);
        container.appendChild(section);
    });
}

// Obtener permisos seleccionados del contenedor
function getSelectedPermisos(container) {
    const checkboxes = container.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// Marcar/desmarcar todos los permisos de una categoría
function toggleCategoriaPermisos(container, categoria, checked) {
    const categoriaElement = container.querySelector(`[data-categoria="${categoria}"]`);
    if (!categoriaElement) return;

    const checkboxes = categoriaElement.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = checked);
}

// Obtener permisos por defecto según rol
function getPermisosPorRol(rol) {
    return PERMISOS_POR_ROL[rol] || [];
}

// Verificar si un permiso es válido
function isPermisoValido(permiso) {
    return Object.values(PERMISOS).includes(permiso);
}

// Filtrar permisos válidos
function filterPermisosValidos(permisos) {
    return permisos.filter(p => isPermisoValido(p));
}

// Comparar permisos
function comparePermisos(permisos1, permisos2) {
    const set1 = new Set(permisos1);
    const set2 = new Set(permisos2);

    const added = permisos2.filter(p => !set1.has(p));
    const removed = permisos1.filter(p => !set2.has(p));
    const unchanged = permisos1.filter(p => set2.has(p));

    return { added, removed, unchanged };
}

// Renderizar cambios de permisos
function renderPermisosChanges(cambios) {
    const parts = [];

    if (cambios.added.length > 0) {
        parts.push(`<strong>Agregados:</strong> ${cambios.added.join(', ')}`);
    }

    if (cambios.removed.length > 0) {
        parts.push(`<strong>Eliminados:</strong> ${cambios.removed.join(', ')}`);
    }

    return parts.join('<br>') || 'Sin cambios';
}
