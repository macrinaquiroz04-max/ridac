-- ============================================================================
-- Script de Gestión Masiva de Permisos - Sistema OCR FGJCDMX
-- Desarrollado por: Eduardo Lozada Quiroz, ISC
-- Cliente: Unidad de Análisis y Contexto (UAyC)
-- Fecha: 27 de Octubre de 2025
-- ============================================================================

-- ============================================================================
-- OPCIÓN 1: ACTIVAR TODOS LOS PERMISOS PARA UN USUARIO
-- ============================================================================
-- Cambia el ID del usuario (ejemplo: 2 = analista)
-- Esto activará puede_ver, puede_buscar y puede_exportar para TODOS sus tomos

UPDATE permisos_tomo 
SET 
    puede_ver = true,
    puede_buscar = true,
    puede_exportar = true
WHERE usuario_id = 2;  -- Cambiar ID según el usuario

-- Ver resultado
SELECT pt.usuario_id, u.username, COUNT(*) as total_permisos_actualizados
FROM permisos_tomo pt
JOIN usuarios u ON pt.usuario_id = u.id
WHERE pt.usuario_id = 2
GROUP BY pt.usuario_id, u.username;

-- ============================================================================
-- OPCIÓN 2: QUITAR SOLO PERMISO DE "VER" A TODOS LOS TOMOS DE UN USUARIO
-- ============================================================================
-- Útil para bloquear visualización pero mantener búsqueda y exportación

UPDATE permisos_tomo 
SET puede_ver = false
WHERE usuario_id = 2;  -- Cambiar ID según el usuario

-- ============================================================================
-- OPCIÓN 3: QUITAR TODOS LOS PERMISOS A UN USUARIO
-- ============================================================================
-- Bloquea completamente el acceso a todos los tomos

UPDATE permisos_tomo 
SET 
    puede_ver = false,
    puede_buscar = false,
    puede_exportar = false
WHERE usuario_id = 2;  -- Cambiar ID según el usuario

-- ============================================================================
-- OPCIÓN 4: CREAR PERMISOS COMPLETOS PARA TODOS LOS TOMOS DE UNA CARPETA
-- ============================================================================
-- Asigna permisos completos para todos los tomos de una carpeta específica

-- Primero ver qué carpetas existen
SELECT id, nombre, COUNT(*) as total_tomos
FROM carpetas c
LEFT JOIN tomos t ON c.id = t.carpeta_id
GROUP BY c.id, c.nombre
ORDER BY c.id;

-- Crear permisos para todos los tomos de la carpeta ID 1
INSERT INTO permisos_tomo (usuario_id, tomo_id, puede_ver, puede_buscar, puede_exportar)
SELECT 
    2 as usuario_id,  -- Cambiar ID del usuario
    t.id as tomo_id,
    true as puede_ver,
    true as puede_buscar,
    true as puede_exportar
FROM tomos t
WHERE t.carpeta_id = 1  -- Cambiar ID de la carpeta
ON CONFLICT (usuario_id, tomo_id) 
DO UPDATE SET
    puede_ver = EXCLUDED.puede_ver,
    puede_buscar = EXCLUDED.puede_buscar,
    puede_exportar = EXCLUDED.puede_exportar;

-- ============================================================================
-- OPCIÓN 5: COPIAR PERMISOS DE UN USUARIO A OTRO
-- ============================================================================
-- Útil para replicar permisos de un usuario existente a uno nuevo

-- Copiar permisos del usuario 2 (analista) al usuario 4 (nuevo usuario)
INSERT INTO permisos_tomo (usuario_id, tomo_id, puede_ver, puede_buscar, puede_exportar)
SELECT 
    4 as usuario_id,  -- ID del usuario DESTINO
    pt.tomo_id,
    pt.puede_ver,
    pt.puede_buscar,
    pt.puede_exportar
FROM permisos_tomo pt
WHERE pt.usuario_id = 2  -- ID del usuario ORIGEN
ON CONFLICT (usuario_id, tomo_id) 
DO UPDATE SET
    puede_ver = EXCLUDED.puede_ver,
    puede_buscar = EXCLUDED.puede_buscar,
    puede_exportar = EXCLUDED.puede_exportar;

-- ============================================================================
-- OPCIÓN 6: ACTIVAR PERMISO "VER" PARA TODOS LOS USUARIOS EN TODOS LOS TOMOS
-- ============================================================================
-- ⚠️ CUIDADO: Esto da acceso a TODOS los usuarios

UPDATE permisos_tomo 
SET puede_ver = true
WHERE usuario_id IN (SELECT id FROM usuarios WHERE rol_id != 1);  -- Excluye admin

-- ============================================================================
-- CONSULTAS ÚTILES PARA VERIFICAR
-- ============================================================================

-- Ver todos los permisos de un usuario
SELECT 
    u.username,
    t.id as tomo_id,
    t.nombre_archivo,
    pt.puede_ver,
    pt.puede_buscar,
    pt.puede_exportar
FROM permisos_tomo pt
JOIN usuarios u ON pt.usuario_id = u.id
JOIN tomos t ON pt.tomo_id = t.id
WHERE pt.usuario_id = 2  -- Cambiar ID del usuario
ORDER BY t.id;

-- Contar permisos por usuario
SELECT 
    u.id,
    u.username,
    COUNT(*) as total_tomos,
    SUM(CASE WHEN pt.puede_ver THEN 1 ELSE 0 END) as con_permiso_ver,
    SUM(CASE WHEN pt.puede_buscar THEN 1 ELSE 0 END) as con_permiso_buscar,
    SUM(CASE WHEN pt.puede_exportar THEN 1 ELSE 0 END) as con_permiso_exportar
FROM usuarios u
LEFT JOIN permisos_tomo pt ON u.id = pt.usuario_id
WHERE u.rol_id != 1  -- Excluye admin
GROUP BY u.id, u.username
ORDER BY u.id;

-- Ver usuarios SIN permisos asignados
SELECT u.id, u.username, u.nombre_completo
FROM usuarios u
LEFT JOIN permisos_tomo pt ON u.id = pt.usuario_id
WHERE pt.id IS NULL AND u.rol_id != 1
GROUP BY u.id, u.username, u.nombre_completo;

-- ============================================================================
-- EJEMPLOS DE USO RÁPIDO
-- ============================================================================

-- EJEMPLO 1: Dar acceso completo al usuario "analista" (ID: 2) en todos sus tomos
-- UPDATE permisos_tomo SET puede_ver = true, puede_buscar = true, puede_exportar = true WHERE usuario_id = 2;

-- EJEMPLO 2: Quitar solo visualización al usuario "analista"
-- UPDATE permisos_tomo SET puede_ver = false WHERE usuario_id = 2;

-- EJEMPLO 3: Ver resultado
-- SELECT t.id, t.nombre_archivo, pt.puede_ver, pt.puede_buscar, pt.puede_exportar FROM permisos_tomo pt JOIN tomos t ON pt.tomo_id = t.id WHERE pt.usuario_id = 2;

-- ============================================================================
-- FIN DEL SCRIPT
-- ============================================================================
-- Firma Digital: ELQ_ISC_UAYC_OCT2025
