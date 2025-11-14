/**
 * Módulo de Análisis Jurídico para Dashboard Usuario
 * Funciones para consultar diligencias, personas, lugares, fechas y alertas
 */

const AnalisisJuridico = {
    carpetaActual: null,
    
    /**
     * Inicializar análisis para una carpeta
     */
    async inicializar(carpetaId) {
        this.carpetaActual = carpetaId;
        await this.cargarEstadisticas();
    },
    
    /**
     * Cargar estadísticas generales
     */
    async cargarEstadisticas() {
        try {
            showLoading('Cargando estadísticas...');
            
            const response = await fetch(`${API_URL}/usuario/carpetas/${this.carpetaActual}/estadisticas`, {
                headers: getAuthHeaders()
            });
            
            if (!response.ok) {
                throw new Error('Error al cargar estadísticas');
            }
            
            const data = await response.json();
            this.mostrarEstadisticas(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar estadísticas: ' + error.message);
        }
    },
    
    /**
     * Mostrar estadísticas en tarjetas
     */
    mostrarEstadisticas(data) {
        const container = document.getElementById('estadisticasContainer');
        
        if (!container) {
            console.warn('⚠️ Container de estadísticas no encontrado');
            return;
        }
        
        if (!data.resumen) {
            container.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    No hay análisis disponible. El administrador debe procesar primero los documentos.
                </div>
            `;
            return;
        }
        
        const { resumen, temporalidad, alertas_por_prioridad } = data;
        
        // Función auxiliar para actualizar elemento de forma segura
        const actualizarElemento = (id, valor) => {
            const elemento = document.getElementById(id);
            if (elemento) {
                elemento.textContent = valor;
            } else {
                console.warn(`⚠️ Elemento ${id} no encontrado`);
            }
        };
        
        // Actualizar cards de estadísticas
        actualizarElemento('totalDiligencias', resumen.total_diligencias || 0);
        actualizarElemento('totalPersonas', resumen.total_personas || 0);
        actualizarElemento('totalLugares', resumen.total_lugares || 0);
        actualizarElemento('totalAlertasActivas', resumen.total_alertas_activas || 0);
        
        // Días de investigación
        if (temporalidad && temporalidad.dias_investigacion) {
            actualizarElemento('diasInvestigacion', temporalidad.dias_investigacion);
        }
        
        // Promedio entre actuaciones
        if (temporalidad && temporalidad.promedio_dias_entre_actuaciones) {
            actualizarElemento('promedioDias', Math.round(temporalidad.promedio_dias_entre_actuaciones));
        }
        
        // Alertas por prioridad
        if (alertas_por_prioridad) {
            this.actualizarAlertasPrioridad(alertas_por_prioridad);
        }
    },
    
    /**
     * Cargar diligencias
     */
    async cargarDiligencias(filtros = {}) {
        try {
            showLoading('Cargando diligencias...');
            
            const params = new URLSearchParams({
                orden: filtros.orden || 'cronologico',
                limite: filtros.limite || 100,
                offset: filtros.offset || 0
            });
            
            if (filtros.tipo) params.append('tipo', filtros.tipo);
            if (filtros.fecha_inicio) params.append('fecha_inicio', filtros.fecha_inicio);
            if (filtros.fecha_fin) params.append('fecha_fin', filtros.fecha_fin);
            
            const response = await fetch(
                `${API_URL}/usuario/carpetas/${this.carpetaActual}/diligencias?${params}`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar diligencias');
            
            const data = await response.json();
            this.mostrarDiligencias(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar diligencias: ' + error.message);
        }
    },
    
    /**
     * Mostrar diligencias en tabla
     */
    mostrarDiligencias(data) {
        const container = document.getElementById('diligenciasTableBody');
        
        if (!data.diligencias || data.diligencias.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        <i class="fas fa-inbox fa-2x text-muted mb-2"></i>
                        <p class="text-muted">No se encontraron diligencias</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        container.innerHTML = data.diligencias.map((dil, index) => `
            <tr>
                <td><span class="badge bg-secondary">${dil.orden || index + 1}</span></td>
                <td>
                    <strong>${this.escaparHTML(dil.tipo_diligencia)}</strong>
                    ${dil.verificado ? '<i class="fas fa-check-circle text-success ms-1" title="Verificado"></i>' : ''}
                    ${dil.tomo_nombre ? `<br><small class="text-muted"><i class="fas fa-book me-1"></i>${this.escaparHTML(dil.tomo_nombre)}</small>` : ''}
                    ${dil.pagina ? `<br><small class="text-primary"><i class="fas fa-file-pdf me-1"></i>Página ${dil.pagina}</small>` : ''}
                </td>
                <td>${dil.fecha ? this.formatearFecha(dil.fecha) : '<em class="text-muted">Sin fecha</em>'}</td>
                <td>${dil.responsable ? this.escaparHTML(dil.responsable) : '<em class="text-muted">-</em>'}</td>
                <td>
                    ${dil.numero_oficio ? `<span class="badge bg-info">${this.escaparHTML(dil.numero_oficio)}</span>` : '-'}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="AnalisisJuridico.verDetalleDiligencia(${dil.id})">
                        <i class="fas fa-eye me-1"></i> Ver
                    </button>
                </td>
            </tr>
        `).join('');
        
        // Actualizar total
        document.getElementById('totalDiligenciasText').textContent = `Total: ${data.total} diligencias`;
    },
    
    /**
     * Cargar personas identificadas
     */
    async cargarPersonas(filtros = {}) {
        try {
            showLoading('Cargando personas...');
            
            const params = new URLSearchParams({
                limite: filtros.limite || 100,
                offset: filtros.offset || 0
            });
            
            if (filtros.rol) params.append('rol', filtros.rol);
            if (filtros.buscar) params.append('buscar', filtros.buscar);
            
            const response = await fetch(
                `${API_URL}/usuario/carpetas/${this.carpetaActual}/personas?${params}`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar personas');
            
            const data = await response.json();
            this.mostrarPersonas(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar personas: ' + error.message);
        }
    },
    
    /**
     * Mostrar personas en tabla
     */
    mostrarPersonas(data) {
        const container = document.getElementById('personasTableBody');
        
        if (!data.personas || data.personas.length === 0) {
            container.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">
                        <i class="fas fa-users fa-2x text-muted mb-2"></i>
                        <p class="text-muted">No se encontraron personas</p>
                    </td>
                </tr>
            `;
            return;
        }
        
        container.innerHTML = data.personas.map(persona => `
            <tr>
                <td>
                    <strong>${this.escaparHTML(persona.nombre)}</strong>
                    ${persona.tomo_nombre ? `<br><small class="text-muted"><i class="fas fa-book me-1"></i>${this.escaparHTML(persona.tomo_nombre)}</small>` : ''}
                    ${persona.pagina_primera_mencion ? `<br><small class="text-primary"><i class="fas fa-file-pdf me-1"></i>Página ${persona.pagina_primera_mencion}</small>` : ''}
                </td>
                <td>
                    ${persona.rol ? `<span class="badge bg-primary">${this.escaparHTML(persona.rol)}</span>` : '-'}
                </td>
                <td>
                    ${persona.direccion ? this.truncar(this.escaparHTML(persona.direccion), 40) : '-'}<br>
                    ${persona.colonia ? `<small class="text-muted">${this.escaparHTML(persona.colonia)}</small>` : ''}
                </td>
                <td>
                    ${persona.telefono ? `<i class="fas fa-phone me-1"></i>${this.escaparHTML(persona.telefono)}` : '-'}
                </td>
                <td class="text-center">
                    <span class="badge bg-info">${persona.total_declaraciones || 0}</span>
                </td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="AnalisisJuridico.verDetallePersona(${persona.id})">
                        <i class="fas fa-eye me-1"></i> Ver
                    </button>
                </td>
            </tr>
        `).join('');
        
        document.getElementById('totalPersonasText').textContent = `Total: ${data.total} personas`;
    },
    
    /**
     * Cargar lugares
     */
    async cargarLugares(filtros = {}) {
        try {
            showLoading('Cargando lugares...');
            
            const params = new URLSearchParams({
                limite: filtros.limite || 100,
                offset: filtros.offset || 0
            });
            
            if (filtros.tipo) params.append('tipo', filtros.tipo);
            if (filtros.buscar) params.append('buscar', filtros.buscar);
            
            const response = await fetch(
                `${API_URL}/usuario/carpetas/${this.carpetaActual}/lugares?${params}`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar lugares');
            
            const data = await response.json();
            this.mostrarLugares(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar lugares: ' + error.message);
        }
    },
    
    /**
     * Mostrar lugares
     */
    mostrarLugares(data) {
        const container = document.getElementById('lugaresContainer');
        
        if (!data.lugares || data.lugares.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-map-marker-alt fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No se encontraron lugares</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.lugares.map(lugar => `
            <div class="col-md-6 mb-3">
                <div class="card h-100">
                    <div class="card-body">
                        <h6 class="card-title">
                            <i class="fas fa-map-pin text-danger me-2"></i>
                            ${this.escaparHTML(lugar.direccion_completa || lugar.nombre)}
                        </h6>
                        ${lugar.tomo_nombre ? `<div class="mb-2"><small class="text-muted"><i class="fas fa-book me-1"></i>${this.escaparHTML(lugar.tomo_nombre)}</small></div>` : ''}
                        ${lugar.pagina ? `<div class="mb-2"><small class="text-primary"><i class="fas fa-file-pdf me-1"></i>Página ${lugar.pagina}</small></div>` : ''}
                        <div class="mt-2">
                            ${lugar.tipo ? `<span class="badge bg-secondary me-1">${this.escaparHTML(lugar.tipo)}</span>` : ''}
                            ${lugar.relevancia ? `<span class="badge bg-warning">${this.escaparHTML(lugar.relevancia)}</span>` : ''}
                        </div>
                        <div class="mt-2 text-muted small">
                            ${lugar.colonia ? `<div><i class="fas fa-home me-1"></i>${this.escaparHTML(lugar.colonia)}</div>` : ''}
                            ${lugar.municipio ? `<div><i class="fas fa-city me-1"></i>${this.escaparHTML(lugar.municipio)}</div>` : ''}
                            ${lugar.frecuencia ? `<div><i class="fas fa-sync me-1"></i>Mencionado ${lugar.frecuencia} veces</div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    },
    
    /**
     * Cargar alertas
     */
    async cargarAlertas(estado = 'activa', prioridad = null) {
        try {
            showLoading('Cargando alertas...');
            
            const params = new URLSearchParams({ estado });
            if (prioridad) params.append('prioridad', prioridad);
            
            const response = await fetch(
                `${API_URL}/usuario/carpetas/${this.carpetaActual}/alertas?${params}`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar alertas');
            
            const data = await response.json();
            this.mostrarAlertas(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar alertas: ' + error.message);
        }
    },
    
    /**
     * Mostrar alertas
     */
    mostrarAlertas(data) {
        const container = document.getElementById('alertasContainer');
        
        if (!data.alertas || data.alertas.length === 0) {
            container.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    No hay alertas activas. Todo en orden.
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.alertas.map(alerta => {
            const colorClase = {
                'crítica': 'danger',
                'alta': 'warning',
                'media': 'info',
                'baja': 'secondary'
            }[alerta.prioridad] || 'secondary';
            
            const iconoClase = {
                'crítica': 'exclamation-triangle',
                'alta': 'exclamation-circle',
                'media': 'info-circle',
                'baja': 'info'
            }[alerta.prioridad] || 'info';
            
            return `
                <div class="alert alert-${colorClase} d-flex align-items-start">
                    <i class="fas fa-${iconoClase} fa-2x me-3"></i>
                    <div class="flex-grow-1">
                        <h6 class="alert-heading mb-1">
                            <span class="badge bg-${colorClase} me-2">${this.escaparHTML(alerta.prioridad).toUpperCase()}</span>
                            ${this.escaparHTML(alerta.titulo)}
                        </h6>
                        <p class="mb-1">${this.escaparHTML(alerta.descripcion)}</p>
                        <small class="text-muted">
                            <i class="fas fa-clock me-1"></i>
                            ${alerta.dias_inactividad} días de inactividad
                            ${alerta.fecha_ultima_actuacion ? 
                                `| Última actuación: ${this.formatearFecha(alerta.fecha_ultima_actuacion)}` : ''}
                        </small>
                    </div>
                </div>
            `;
        }).join('');
    },
    
    /**
     * Cargar línea de tiempo
     */
    async cargarLineaTiempo() {
        try {
            showLoading('Cargando línea de tiempo...');
            
            const response = await fetch(
                `${API_URL}/usuario/carpetas/${this.carpetaActual}/linea-tiempo`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar línea de tiempo');
            
            const data = await response.json();
            this.mostrarLineaTiempo(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar línea de tiempo: ' + error.message);
        }
    },
    
    /**
     * Mostrar línea de tiempo
     */
    mostrarLineaTiempo(data) {
        const container = document.getElementById('lineaTiempoContainer');
        
        if (!data.eventos || data.eventos.length === 0) {
            container.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-calendar-times fa-3x text-muted mb-3"></i>
                    <p class="text-muted">No hay eventos en la línea de tiempo</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.eventos.map((evento, index) => `
            <div class="timeline-item">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <div class="timeline-date">${this.formatearFecha(evento.fecha)}</div>
                    <div class="timeline-title">${this.escaparHTML(evento.titulo)}</div>
                    <div class="timeline-description">${this.escaparHTML(evento.descripcion)}</div>
                    ${evento.responsable ? `<div class="text-muted small mt-1">
                        <i class="fas fa-user me-1"></i>${this.escaparHTML(evento.responsable)}
                    </div>` : ''}
                    ${evento.oficio ? `<div class="text-muted small">
                        <i class="fas fa-file-alt me-1"></i>${this.escaparHTML(evento.oficio)}
                    </div>` : ''}
                    ${evento.pagina ? `<div class="text-primary small">
                        <i class="fas fa-file-pdf me-1"></i>Página ${evento.pagina}
                    </div>` : ''}
                </div>
            </div>
        `).join('');
    },
    
    /**
     * Ver detalle de diligencia
     */
    async verDetalleDiligencia(id) {
        try {
            showLoading('Cargando detalle...');
            
            const response = await fetch(
                `${API_URL}/usuario/diligencias/${id}`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar diligencia');
            
            const data = await response.json();
            this.mostrarModalDiligencia(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error al cargar diligencia: ' + error.message);
        }
    },
    
    /**
     * Mostrar modal con detalle completo de diligencia
     */
    mostrarModalDiligencia(data) {
        const modal = new bootstrap.Modal(document.getElementById('modalDetalleDiligencia'));
        
        // Información básica
        document.getElementById('modalDilTipo').innerHTML = `<span class="badge bg-primary">${this.escaparHTML(data.tipo_diligencia)}</span>`;
        document.getElementById('modalDilFecha').textContent = data.fecha_diligencia ? this.formatearFecha(data.fecha_diligencia) : 'Sin fecha';
        document.getElementById('modalDilResponsable').textContent = data.responsable || 'No especificado';
        document.getElementById('modalDilOficio').innerHTML = data.numero_oficio ? `<code>${this.escaparHTML(data.numero_oficio)}</code>` : 'N/A';
        document.getElementById('modalDilPagina').innerHTML = `<span class="badge bg-info">Página ${data.numero_pagina || 'N/A'}</span>`;
        
        // Texto completo
        document.getElementById('modalDilTextoCompleto').textContent = data.texto_contexto || data.descripcion || 'Sin texto disponible';
        
        // Si tiene párrafo estructurado, mostrar análisis
        if (data.parrafo_estructurado) {
            this.mostrarParrafoEstructurado(data.parrafo_estructurado);
        } else {
            // Ocultar secciones de análisis estructurado
            document.getElementById('modalDilEstructuradoCard').style.display = 'none';
            document.getElementById('modalDilResumenCard').style.display = 'none';
            document.getElementById('modalDilElementosCard').style.display = 'none';
        }
        
        modal.show();
    },
    
    /**
     * Mostrar información del párrafo estructurado
     */
    mostrarParrafoEstructurado(parrafo) {
        // Card de análisis estructurado
        const cardEstructurado = document.getElementById('modalDilEstructuradoCard');
        cardEstructurado.style.display = 'block';
        
        // Tipo de documento
        const tiposDoc = {
            'oficio_solicitud': '📄 Oficio de Solicitud',
            'oficio_informativo': '📋 Oficio Informativo',
            'oficio_general': '📄 Oficio General',
            'constancia': '📝 Constancia',
            'comunicado_oficial': '📢 Comunicado Oficial',
            'acta_hechos': '⚖️ Acta de Hechos',
            'actuacion_ministerial': '🏛️ Actuación Ministerial',
            'documento_general': '📃 Documento General'
        };
        
        document.getElementById('modalDilTipoDoc').textContent = tiposDoc[parrafo.tipo_documento] || parrafo.tipo_documento;
        
        // Relevancia
        const relevancia = parrafo.relevancia || 0;
        const relevanciaPercent = Math.min(100, relevancia * 10);
        document.getElementById('modalDilRelevancia').innerHTML = `<strong>${relevancia}</strong>/10`;
        document.getElementById('modalDilRelevanciaBar').style.width = relevanciaPercent + '%';
        
        // Color según relevancia
        const barElement = document.getElementById('modalDilRelevanciaBar');
        if (relevancia >= 7) {
            barElement.className = 'progress-bar bg-success';
        } else if (relevancia >= 4) {
            barElement.className = 'progress-bar bg-warning';
        } else {
            barElement.className = 'progress-bar bg-danger';
        }
        
        // Longitud
        document.getElementById('modalDilLongitud').textContent = (parrafo.longitud || 0).toLocaleString();
        
        // Resumen
        if (parrafo.resumen) {
            document.getElementById('modalDilResumenCard').style.display = 'block';
            document.getElementById('modalDilResumen').textContent = parrafo.resumen;
        } else {
            document.getElementById('modalDilResumenCard').style.display = 'none';
        }
        
        // Elementos identificados
        const elementos = parrafo.elementos || {};
        let hayElementos = false;
        
        // Fechas detalladas
        if (elementos.fechas_detalladas && elementos.fechas_detalladas.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilFechasContainer').style.display = 'block';
            document.getElementById('modalDilFechas').innerHTML = elementos.fechas_detalladas.map((fecha, idx) => `
                <div class="mb-2 p-2 bg-light rounded">
                    <div><strong>${fecha.fecha_texto}</strong></div>
                    <small class="text-muted">${this.truncar(fecha.contexto, 100)}</small>
                </div>
            `).join('');
        } else {
            document.getElementById('modalDilFechasContainer').style.display = 'none';
        }
        
        // Oficios
        if (elementos.oficio && elementos.oficio.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilOficiosContainer').style.display = 'block';
            document.getElementById('modalDilOficios').innerHTML = elementos.oficio.map(of => 
                `<span class="badge bg-info mb-1 me-1">${this.escaparHTML(of)}</span>`
            ).join('');
        } else {
            document.getElementById('modalDilOficiosContainer').style.display = 'none';
        }
        
        // Carpetas
        if (elementos.carpeta && elementos.carpeta.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilCarpetasContainer').style.display = 'block';
            document.getElementById('modalDilCarpetas').innerHTML = elementos.carpeta.map(carp => 
                `<span class="badge bg-warning text-dark mb-1 me-1">${this.escaparHTML(carp)}</span>`
            ).join('');
        } else {
            document.getElementById('modalDilCarpetasContainer').style.display = 'none';
        }
        
        // Titulares
        if (elementos.nombre_titular && elementos.nombre_titular.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilTitularesContainer').style.display = 'block';
            document.getElementById('modalDilTitulares').innerHTML = elementos.nombre_titular.map(nom => 
                `<div class="mb-1"><i class="fas fa-user me-1"></i>${this.escaparHTML(nom)}</div>`
            ).join('');
        } else {
            document.getElementById('modalDilTitularesContainer').style.display = 'none';
        }
        
        // Nombres mencionados
        if (elementos.nombres_mencionados && elementos.nombres_mencionados.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilNombresContainer').style.display = 'block';
            document.getElementById('modalDilNombres').innerHTML = elementos.nombres_mencionados.map(nom => 
                `<span class="badge bg-secondary mb-1 me-1">${this.escaparHTML(nom)}</span>`
            ).join('');
        } else {
            document.getElementById('modalDilNombresContainer').style.display = 'none';
        }
        
        // Unidades
        if (elementos.unidad && elementos.unidad.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilUnidadesContainer').style.display = 'block';
            document.getElementById('modalDilUnidades').innerHTML = elementos.unidad.map(uni => 
                `<span class="badge bg-success mb-1 me-1">${this.escaparHTML(uni)}</span>`
            ).join('');
        } else {
            document.getElementById('modalDilUnidadesContainer').style.display = 'none';
        }
        
        // Delitos
        if (elementos.delito && elementos.delito.length > 0) {
            hayElementos = true;
            document.getElementById('modalDilDelitosContainer').style.display = 'block';
            document.getElementById('modalDilDelitos').innerHTML = elementos.delito.map(del => 
                `<span class="badge bg-danger mb-1 me-1">${this.escaparHTML(del)}</span>`
            ).join('');
        } else {
            document.getElementById('modalDilDelitosContainer').style.display = 'none';
        }
        
        // Mostrar u ocultar card de elementos
        if (hayElementos) {
            document.getElementById('modalDilElementosCard').style.display = 'block';
        } else {
            document.getElementById('modalDilElementosCard').style.display = 'none';
        }
    },
    
    /**
     * Ver detalle de persona con declaraciones
     */
    async verDetallePersona(personaId) {
        try {
            showLoading('Cargando información...');
            
            const response = await fetch(
                `${API_URL}/usuario/personas/${personaId}/declaraciones`,
                { headers: getAuthHeaders() }
            );
            
            if (!response.ok) throw new Error('Error al cargar declaraciones');
            
            const data = await response.json();
            this.mostrarModalPersona(data);
            
            hideLoading();
        } catch (error) {
            console.error('Error:', error);
            hideLoading();
            showError('Error: ' + error.message);
        }
    },
    
    /**
     * Mostrar modal con declaraciones de persona
     */
    mostrarModalPersona(data) {
        const modal = new bootstrap.Modal(document.getElementById('modalDetallePersona'));
        
        document.getElementById('modalPersonaNombre').textContent = data.persona.nombre;
        document.getElementById('modalPersonaRol').textContent = data.persona.rol || 'Sin rol';
        
        const tbody = document.getElementById('modalDeclaracionesBody');
        
        if (data.declaraciones && data.declaraciones.length > 0) {
            tbody.innerHTML = data.declaraciones.map((decl, index) => `
                <tr>
                    <td>${index + 1}</td>
                    <td>${this.formatearFecha(decl.fecha)}</td>
                    <td>${this.escaparHTML(decl.tipo || 'N/A')}</td>
                    <td>${decl.resumen ? this.truncar(this.escaparHTML(decl.resumen), 100) : '-'}</td>
                    <td>Pág. ${decl.pagina || 'N/A'}</td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay declaraciones registradas</td></tr>';
        }
        
        modal.show();
    },
    
    // Utilidades
    
    formatearFecha(fecha) {
        if (!fecha) return '-';
        const d = new Date(fecha + 'T00:00:00');
        return d.toLocaleDateString('es-MX', { 
            year: 'numeric', 
            month: 'long', 
            day: 'numeric' 
        });
    },
    
    escaparHTML(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    },
    
    truncar(texto, longitud) {
        if (!texto || texto.length <= longitud) return texto;
        return texto.substring(0, longitud) + '...';
    },
    
    actualizarAlertasPrioridad(alertas) {
        const container = document.getElementById('alertasPrioridadContainer');
        
        // Validar que el contenedor existe
        if (!container) {
            console.warn('⚠️ Container alertasPrioridadContainer no encontrado');
            return;
        }
        
        if (!alertas || Object.keys(alertas).length === 0) {
            container.innerHTML = '<div class="text-muted text-center">Sin alertas</div>';
            return;
        }
        
        container.innerHTML = Object.entries(alertas).map(([prioridad, total]) => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="badge bg-${this.colorPrioridad(prioridad)}">${prioridad}</span>
                <strong>${total}</strong>
            </div>
        `).join('');
    },
    
    colorPrioridad(prioridad) {
        const colores = {
            'crítica': 'danger',
            'alta': 'warning',
            'media': 'info',
            'baja': 'secondary'
        };
        return colores[prioridad] || 'secondary';
    }
};

// Funciones auxiliares globales
function showLoading(mensaje = 'Cargando...') {
    // Implementar según tu sistema actual
    (() => {})('Loading:', mensaje);
}

function hideLoading() {
    (() => {})('Loading hidden');
}

function showError(mensaje) {
    alert('Error: ' + mensaje);
}

function showInfo(mensaje) {
    alert(mensaje);
}

function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// API_URL ya está definido en config.js
