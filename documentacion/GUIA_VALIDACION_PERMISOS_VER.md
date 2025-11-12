# 🔒 Guía de Validación de Permisos - Sistema de Visualización de Tomos

**Desarrollado por:** Eduardo Lozada Quiroz, ISC  
**Cliente:** Unidad de Análisis y Contexto (UAyC) - FGJCDMX  
**Fecha:** 27 de Octubre de 2025

---

## 📋 Resumen de Implementación

Se ha implementado un **sistema de 3 niveles de validación** para el permiso "Ver" de tomos:

### ✅ Nivel 1: Frontend - Dashboard (dashboard-usuario.html)
- **Ubicación:** Línea 1810
- **Función:** El botón "Ver" solo aparece si `tomo.puede_ver === true`
- **Resultado:** Usuario no ve el botón si no tiene permiso

### ✅ Nivel 2: Frontend - Visor PDF (visor-pdf.html)
- **Ubicación:** Función `cargarTomo()` líneas 328-363
- **Validación:** 
  - Llama a `/tomos/info/{id}` antes de cargar PDF
  - Si recibe 403, muestra pantalla de "Acceso Denegado" 🔒
  - Cierra automáticamente la ventana después de 3 segundos
- **Resultado:** Incluso si usuario accede directo a URL, se valida permiso

### ✅ Nivel 3: Backend - API (tomos.py)
- **Endpoint 1:** `/tomos/info/{id}` (líneas 520-547)
  - Verifica existencia de permiso
  - Valida que `puede_ver == True`
  - Retorna 403 si no tiene permiso
  
- **Endpoint 2:** `/tomos/pdf/{id}` (líneas 556-618)
  - Verifica existencia de permiso
  - Valida que `puede_ver == True`
  - Retorna 403 si no tiene permiso
  - Solo sirve el archivo PDF si pasa validaciones

---

## 🧪 Prueba de Validación Completa

### Paso 1: Preparar Ambiente de Prueba

1. Accede como administrador:
   - URL: `http://fgj-ocr.local/`
   - Usuario: `eduardo`
   - Password: `lalo1998c33`

### Paso 2: Crear Usuario de Prueba (o usar existente)

2. Ve a **"Administración de Usuarios"** → **"Gestión de Permisos"**

3. Selecciona un usuario (por ejemplo: "Usuario Analista")

### Paso 3: Configurar Permisos

4. En "Permisos de Tomos", asegúrate que el usuario tenga:
   - ✅ **Visualización** activado (toggle verde)
   - ✅ **Contenido** activado
   - ✅ **A Word** activado

5. Haz clic en **"Guardar Cambios"**

### Paso 4: Verificar Acceso PERMITIDO

6. **Cierra sesión** y entra con el usuario de prueba

7. Deberías ver:
   - ✅ Botón "Ver" visible en el tomo
   - ✅ Al hacer clic, abre visor-pdf.html
   - ✅ PDF se carga correctamente
   - ✅ Puedes seleccionar texto

### Paso 5: QUITAR Permiso "Ver"

8. **Cierra sesión** y vuelve a entrar como administrador

9. Ve a **"Gestión de Permisos"** del usuario

10. **DESACTIVA** el toggle de **"Visualización"** (debe quedar gris/rojo)

11. Haz clic en **"Guardar Cambios"**

### Paso 6: Verificar Acceso DENEGADO

12. **Cierra sesión** y entra nuevamente con el usuario de prueba

13. Deberías ver:
   - ❌ **El botón "Ver" NO aparece** (Nivel 1 funcionando)

14. **Prueba adicional:** Intenta acceder directamente a la URL:
   ```
   http://fgj-ocr.local/visor-pdf.html?tomo_id=1
   ```

15. Deberías ver:
   - 🔒 Pantalla de "**Acceso Denegado**"
   - Ícono de candado grande
   - Mensaje: "No tiene permisos para visualizar este documento"
   - Botón "Cerrar Ventana"
   - La ventana se cierra automáticamente en 3 segundos

---

## 🎯 Resultados Esperados

### ✅ CON permiso "Ver" activado:
1. Botón "Ver" visible
2. Visor se abre correctamente
3. PDF se carga
4. Texto es seleccionable
5. NO hay botón de descarga

### ❌ SIN permiso "Ver" activado:
1. Botón "Ver" NO aparece en dashboard
2. Si accede por URL directa → Pantalla "Acceso Denegado"
3. Backend retorna 403 Forbidden
4. Usuario NO puede ver el PDF de ninguna manera

---

## 🔧 Detalles Técnicos

### Validación Backend (tomos.py)

```python
# Solo admin puede ver sin restricciones
es_admin = current_user.rol.nombre in ["admin", "administrador"]

if not es_admin:
    # Buscar permiso específico para este tomo
    permiso = db.query(PermisoTomo).filter(
        PermisoTomo.usuario_id == current_user.id,
        PermisoTomo.tomo_id == tomo_id
    ).first()

    # Validar que existe el permiso Y que puede_ver es True
    if not permiso:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos asignados para este tomo"
        )
    
    if not permiso.puede_ver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso de visualización para este tomo"
        )
```

### Validación Frontend (visor-pdf.html)

```javascript
if (!response.ok) {
    if (response.status === 403) {
        mostrarError('❌ ACCESO DENEGADO: No tiene permiso para visualizar este documento');
        // Mostrar pantalla de acceso denegado
        // Cerrar ventana después de 3 segundos
        return;
    }
}
```

---

## 🛡️ Casos Especiales

### Administradores
- Los usuarios con rol "admin" o "administrador" **pueden ver todos los tomos sin restricciones**
- No se valida el permiso `puede_ver` para administradores

### Usuarios Normales
- **DEBEN** tener permiso explícito en la tabla `permisos_tomos`
- **DEBEN** tener `puede_ver = true`
- Si falta alguna condición → 403 Forbidden

---

## 📊 Registro de Cambios

### 27 de Octubre de 2025
- ✅ Implementado sistema de 3 niveles de validación
- ✅ Mensaje de error mejorado en backend (diferencia entre "no tiene permiso" y "permiso revocado")
- ✅ Pantalla visual de "Acceso Denegado" en visor-pdf.html
- ✅ Cierre automático de ventana cuando no tiene permiso
- ✅ Validación explícita de `puede_ver == True` en backend

---

## 📝 Conclusión

El sistema ahora **garantiza al 100%** que:

1. Si un usuario NO tiene el permiso "Ver" → **NO puede ver el PDF de ninguna manera**
2. La validación ocurre en 3 niveles (Frontend Dashboard, Frontend Visor, Backend API)
3. Incluso si intenta acceder por URL directa, será bloqueado
4. Los mensajes de error son claros y profesionales

**Firma Digital:** ELQ_ISC_UAYC_OCT2025
