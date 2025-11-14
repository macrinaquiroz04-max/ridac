                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                # 🔒 Seguridad de Acceso - Páginas de Administrador

## ⚠️ Problema Identificado y Corregido

**Fecha**: 2025-01-XX
**Criticidad**: 🔴 ALTA
**Estado**: ✅ RESUELTO

### Descripción del Problema

Se detectó que usuarios con rol **no-admin** podían acceder a páginas administrativas escribiendo directamente la URL en el navegador. 

Las páginas solo ocultaban botones de la interfaz (`display: none`), pero **NO bloqueaban el acceso** a la página completa.

#### Páginas Afectadas (TODAS CORREGIDAS):
1. ✅ `carpetas.html` - Gestión de Expedientes
2. ✅ `usuarios.html` - Gestión de Usuarios  
3. ✅ `permisos.html` - Gestión de Permisos
4. ✅ `auditoria.html` - Auditoría del Sistema
5. ✅ `limpieza-personas.html` - Limpieza de Personas
6. ✅ `correccion-diligencias.html` - Corrección de Diligencias
7. ✅ `analisis-ia.html` - Análisis con IA

---

## ✅ Solución Implementada

### Validación Estricta de Roles

Todas las páginas administrativas ahora implementan:

```javascript
// 🔒 VALIDACIÓN CRÍTICA: Solo administradores pueden acceder
const token = localStorage.getItem('token');
if (!token) {
    window.location.href = 'index';
    return;
}

const response = await fetch(`${API_URL}/auth/me`, {
    headers: { 'Authorization': `Bearer ${token}` }
});

const user = await response.json();

// Array de roles permitidos (incluye variaciones)
const rolesAdmin = ['admin', 'Admin', 'Administrador', 'administrador', 'Director', 'director'];

if (!rolesAdmin.includes(user.rol)) {
    console.warn('⛔ Acceso denegado: Usuario sin permisos de administrador');
    alert('⛔ Acceso Denegado\n\nEsta página es solo para administradores.\nSerá redirigido a su dashboard.');
    window.location.href = 'dashboard-usuario';
    return;
}
```

### Características de Seguridad

1. **✅ Validación Inmediata**: Se ejecuta ANTES de cargar cualquier dato
2. **✅ Redirect Automático**: Usuarios no-admin son redirigidos a su dashboard
3. **✅ Roles Flexibles**: Soporta variaciones como 'admin', 'Admin', 'Director', etc.
4. **✅ Logging de Seguridad**: `console.warn()` registra intentos de acceso no autorizados
5. **✅ Limpieza de Sesión**: Si el token es inválido, se limpia localStorage

---

## 🔐 Roles de Administrador Soportados

```javascript
const rolesAdmin = [
    'admin',
    'Admin',
    'Administrador',
    'administrador',
    'Director',
    'director'
];
```

> **Nota**: Si necesitas agregar más roles administrativos, edita este array en cada página.

---

## 🧪 Pruebas de Seguridad

### ✅ Casos Probados

1. **Usuario Admin**: Acceso completo ✅
2. **Usuario Director**: Acceso completo ✅  
3. **Usuario Normal**: Bloqueado y redirigido ✅
4. **Sin Token**: Redirigido a login ✅
5. **Token Inválido**: Sesión limpiada y redirigido ✅

### Flujo de Redirección

```
Usuario No-Admin intenta acceder
         ↓
Validación detecta rol inválido
         ↓
Muestra alerta "⛔ Acceso Denegado"
         ↓
Redirige a 'dashboard-usuario'
         ↓
Usuario ve su dashboard normal
```

---

## 📊 Estado de Protección

| Página | Estado | Validación |
|--------|--------|-----------|
| `carpetas.html` | 🟢 Protegida | ✅ Role check completo |
| `usuarios.html` | 🟢 Protegida | ✅ Role check completo |
| `permisos.html` | 🟢 Protegida | ✅ Role check completo |
| `auditoria.html` | 🟢 Protegida | ✅ Role check completo |
| `limpieza-personas.html` | 🟢 Protegida | ✅ Role check completo |
| `correccion-diligencias.html` | 🟢 Protegida | ✅ Role check completo |
| `analisis-ia.html` | 🟢 Protegida | ✅ Role check completo |
| `dashboard.html` | 🟡 Mixta | Solo oculta botones admin |
| `dashboard-usuario.html` | 🟢 Pública | Usuarios normales |

---

## 🚀 Recomendaciones Adicionales

### Backend (Ya implementado)
✅ Los endpoints `/admin/*` ya validan roles en el backend
✅ FastAPI verifica tokens JWT en cada request
✅ Decorador `@admin_required` protege rutas sensibles

### Frontend (Implementado ahora)
✅ Validación de roles en cada página administrativa
✅ Redirect automático para usuarios no autorizados
✅ Mensajes claros de "Acceso Denegado"

### Mejoras Futuras (Opcionales)
- [ ] Implementar middleware de autenticación global
- [ ] Crear componente reutilizable de AuthGuard
- [ ] Agregar audit log de intentos de acceso no autorizados
- [ ] Rate limiting para prevenir fuerza bruta

---

## 🔍 Cómo Verificar la Seguridad

### Prueba Manual

1. Crea un usuario sin rol admin:
```bash
# Desde psql
INSERT INTO usuarios (email, nombre, hashed_password, rol) 
VALUES ('test@test.com', 'Usuario Prueba', 'hash', 'usuario');
```

2. Inicia sesión con ese usuario

3. Intenta acceder a cualquier URL admin:
   - `http://localhost/carpetas.html`
   - `http://localhost/usuarios.html`
   - `http://localhost/auditoria.html`

4. **Resultado esperado**: 
   - ⛔ Alerta de "Acceso Denegado"
   - Redirect automático a `dashboard-usuario`

### Verificación en DevTools

```javascript
// En la consola del navegador, verás:
⛔ Acceso denegado: Usuario sin permisos de administrador
```

---

## 📝 Historial de Cambios

### 2025-01-XX - Implementación Inicial
- ✅ Agregada validación de roles a 7 páginas administrativas
- ✅ Implementado redirect automático
- ✅ Agregados mensajes de error claros
- ✅ Documentación de seguridad creada

---

## ⚠️ IMPORTANTE

**Nunca confíes solo en la seguridad del frontend**. Siempre valida permisos en el backend.

La validación del frontend es para:
- ✅ Mejorar UX (evitar clicks innecesarios)
- ✅ Feedback inmediato al usuario
- ✅ Reducir carga innecesaria del servidor

**La validación del backend es obligatoria para:**
- 🔒 Seguridad real
- 🔒 Protección de datos
- 🔒 Auditoría y compliance

---

## � Sistema de Renovación de Tokens

### Implementación

Se agregó el sistema **AuthManager** que maneja automáticamente:

#### 1. **Renovación Automática de Tokens**
- ✅ Verifica el token cada **14 minutos** (expira a los 15)
- ✅ Intenta renovar usando refresh_token si está disponible
- ✅ Valida que el token actual sigue siendo válido
- ✅ Cierra sesión automáticamente si el token expira

#### 2. **Detección de Inactividad**
- ✅ Monitorea actividad del usuario (clicks, movimiento, scroll, teclado)
- ✅ Tiempo máximo de inactividad: **30 minutos**
- ✅ Cierre automático de sesión por inactividad
- ✅ Indicador visual del tiempo restante

#### 3. **Verificación Periódica**
- ✅ Verifica el estado de la sesión cada **1 minuto**
- ✅ Detecta tokens inválidos o sesiones cerradas en el backend
- ✅ Limpia localStorage y redirige al login si es necesario

### Archivos Implementados

```
frontend/js/
├── auth-manager.js       → Gestión de autenticación y renovación
└── session-indicator.js  → Indicador visual de estado de sesión
```

### Configuración

Los tiempos se pueden ajustar en `auth-manager.js`:

```javascript
this.TOKEN_REFRESH_INTERVAL = 14 * 60 * 1000;  // 14 minutos
this.INACTIVITY_TIMEOUT = 30 * 60 * 1000;      // 30 minutos
this.CHECK_INTERVAL = 60 * 1000;               // 1 minuto
```

### Indicador Visual de Sesión

El sistema muestra un indicador en la esquina inferior derecha con 3 estados:

1. **🟢 Verde (Activo)**: Sesión normal, < 50% del tiempo de inactividad
2. **🟡 Amarillo (Advertencia)**: 50-80% del tiempo transcurrido
3. **🔴 Rojo (Peligro)**: > 80% del tiempo, sesión por expirar

**Características del indicador**:
- Click para minimizar/maximizar
- Muestra tiempo restante en minutos y segundos
- Animación de pulso cuando hay advertencia/peligro

### Eventos que Resetean la Inactividad

```javascript
['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click']
```

Cualquier interacción del usuario reinicia el contador.

### Mensajes al Usuario

El sistema muestra alertas claras cuando:
- ⚠️ **Sesión expirada**: "Su sesión ha expirado. Por favor, inicie sesión nuevamente."
- ⏰ **Inactividad**: "Su sesión ha sido cerrada por inactividad."
- ❌ **Token inválido**: "Su sesión ya no es válida. Por favor, inicie sesión nuevamente."

---

## �📞 Contacto

Si encuentras algún problema de seguridad, repórtalo inmediatamente al equipo de desarrollo.

**No intentar explotar vulnerabilidades**. Este sistema es para uso oficial de FGJCDMX.
