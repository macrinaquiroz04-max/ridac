# 📚 Sistema de Tutoriales Interactivos

## ✅ Implementación Completada

Se ha implementado un **sistema de tutoriales interactivos** para facilitar el onboarding de nuevos usuarios (tanto administradores como usuarios regulares).

---

## 🎯 Características

### ✨ Tutorial Base (`tutorial.js`)
- **Modal con overlay oscuro** que bloquea interacción con el resto de la página
- **Resaltado de elementos** con animación de pulso para guiar visualmente
- **Barra de progreso** mostrando paso X de Y
- **Navegación completa**: Anterior, Siguiente, Saltar
- **Persistencia con localStorage**: Solo se muestra una vez por usuario
- **Reiniciable**: Se puede volver a mostrar desde el menú de ayuda
- **Scroll automático**: Se desplaza al elemento resaltado
- **Mensaje de finalización**: Confirmación al completar el tutorial

### 👨‍💼 Tutorial de Administrador (`tutorial-admin.js`)
**6 pasos específicos:**
1. **Bienvenida** - Introducción al sistema con disclaimer
2. **Gestionar Usuarios** - Cómo crear y administrar usuarios
3. **Subir Carpetas y Tomos** - Proceso de carga de PDFs
4. **Asignar Permisos** - Sistema de permisos granulares
5. **Auditoría del Sistema** - Monitoreo de actividad
6. **Resumen final** - Recapitulación y consejos

**Elementos resaltados:**
- `#btnUsuarios` - Botón Gestionar Usuarios
- `button[onclick*="carpetas"]` - Botón Gestionar Carpetas
- `#btnAuditoria` - Botón Auditoría

### 👤 Tutorial de Usuario Regular (`tutorial-usuario.js`)
**8 pasos específicos:**
1. **Bienvenida** - Introducción y disclaimer sobre OCR imperfecto
2. **Tomos Disponibles** - Explicación de las tarjetas de tomos
3. **Visor de Documentos** - Funciones del visor PDF
4. **Búsqueda de Texto** - Búsqueda simple y avanzada
5. **Búsqueda Semántica** - Búsqueda por conceptos
6. **Exportar Documentos** - Descarga de PDFs originales
7. **Análisis Jurídico Avanzado** - Herramientas de análisis con IA
8. **Consejos Finales** - Tips y mejores prácticas

**Elementos resaltados:**
- `#listado-tomos` - Sección de tomos disponibles
- `button[onclick*="semantica"]` - Botón búsqueda semántica

---

## 🔧 Integración

### Dashboard Administrador (`dashboard.html`)
```html
<!-- Al final del <body>, antes de </body> -->
<script src="js/tutorial.js"></script>
<script src="js/tutorial-admin.js"></script>
```

**Botón de ayuda agregado:**
```html
<button class="btn-logout" onclick="reiniciarTutorial()">
    ❓ Ayuda
</button>
```

### Dashboard Usuario (`dashboard-usuario.html`)
```html
<!-- Al final del <body>, antes de </body> -->
<script src="js/tutorial.js"></script>
<script src="js/tutorial-usuario.js"></script>
```

**Botón de ayuda agregado:**
```html
<button class="btn btn-outline-warning btn-sm" onclick="reiniciarTutorial()">
    <i class="fas fa-question-circle"></i> Ayuda
</button>
```

---

## 📖 Uso

### Para Usuarios Nuevos
- Al **iniciar sesión por primera vez**, el tutorial se muestra automáticamente
- Puede **navegar** con los botones "Siguiente" y "Anterior"
- Puede **saltar** el tutorial en cualquier momento
- El sistema **recuerda** que ya vio el tutorial (localStorage)

### Para Reiniciar el Tutorial
1. Hacer clic en el botón **"❓ Ayuda"** en la esquina superior derecha
2. El tutorial se reiniciará desde el paso 1
3. O ejecutar en consola: `tutorial.reiniciar()`

### Para Desarrolladores
```javascript
// Crear un nuevo tutorial
const miTutorial = new TutorialInteractivo(
    pasos,              // Array de pasos
    'nombre_tutorial'   // Nombre único para localStorage
);

// Iniciar el tutorial
miTutorial.iniciar();

// Reiniciar (borrar localStorage y volver a mostrar)
miTutorial.reiniciar();
```

---

## 🎨 Estructura de un Paso

```javascript
{
    icono: '🎯',                    // Emoji para el título
    titulo: 'Título del Paso',      // Título mostrado
    elemento: '#selector',          // (Opcional) Selector CSS a resaltar
    descripcion: `                  // HTML con la descripción
        Texto explicativo con <strong>formato</strong>
    `,
    nota: 'Nota adicional'          // (Opcional) Texto en cursiva al final
}
```

---

## 💾 Persistencia

El sistema usa **localStorage** para recordar que un usuario ya vio el tutorial:

```javascript
localStorage.setItem('tutorial_dashboard_admin_visto', 'true');
localStorage.setItem('tutorial_dashboard_usuario_visto', 'true');
```

Para **forzar que vuelva a aparecer**, borrar localStorage:
```javascript
localStorage.clear();
// O específicamente:
localStorage.removeItem('tutorial_dashboard_admin_visto');
```

---

## 🎯 Disclaimers Incluidos

Ambos tutoriales incluyen mensajes claros sobre las limitaciones:

✅ **"El sistema NO es perfecto"**  
✅ **"El OCR puede tener errores"**  
✅ **"Depende de la calidad del escaneo"**  
✅ **"Reportar problemas al administrador"**

---

## 🚀 Próximos Pasos Sugeridos

- [ ] Agregar tutorial para la página de **Gestión de Permisos**
- [ ] Crear tutorial para el **Visor PDF** con funciones avanzadas
- [ ] Tutorial para **Búsqueda Semántica** con ejemplos prácticos
- [ ] Agregar **videos cortos** en algunos pasos (opcional)
- [ ] Tracking de qué pasos causan más "saltar" (analítica)

---

## ✅ Estado Actual

| Componente | Estado | Archivo |
|------------|--------|---------|
| **Clase Base** | ✅ Completo | `frontend/js/tutorial.js` |
| **Tutorial Admin** | ✅ Completo | `frontend/js/tutorial-admin.js` |
| **Tutorial Usuario** | ✅ Completo | `frontend/js/tutorial-usuario.js` |
| **Integración Dashboard Admin** | ✅ Completo | `frontend/dashboard.html` |
| **Integración Dashboard Usuario** | ✅ Completo | `frontend/dashboard-usuario.html` |
| **Botón Ayuda Admin** | ✅ Completo | Header dashboard.html |
| **Botón Ayuda Usuario** | ✅ Completo | Navbar dashboard-usuario.html |

---

## 🎓 Retroalimentación de Usuarios

El tutorial está diseñado para ser **"a prueba de tontos"** como solicitado:

✅ Lenguaje claro y directo  
✅ Pasos numerados y secuenciales  
✅ Elementos visuales resaltados  
✅ Ejemplos concretos  
✅ Disclaimers sobre limitaciones  
✅ Opción de saltar si ya saben  
✅ Accesible desde menú de ayuda  

---

**Última actualización:** 10 de noviembre de 2025  
**Autor:** Sistema OCR FGJCDMX - Eduardo
