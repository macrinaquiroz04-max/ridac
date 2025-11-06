-- Insertar roles base
INSERT INTO roles (nombre, codigo, descripcion, nivel_acceso) VALUES
('Administrador', 'ADMIN', 'Control total del sistema', 100),
('Director', 'DIRECTOR', 'Acceso y gestión de tomos a nivel directivo', 80),
('Subdirector', 'SUBDIRECTOR', 'Acceso y gestión limitada de tomos', 60),
('analista', 'ANALISTA', 'Acceso básico a tomos asignados', 40);

-- Configurar permisos por defecto según el rol
-- Estos INSERT se deberían ejecutar cuando se crea un nuevo usuario con su respectivo rol
-- El siguiente es solo un ejemplo de cómo se vería para un analista:
/*
INSERT INTO permisos_tomo (usuario_id, tomo_id, puede_ver, puede_buscar, puede_ver_sellos, 
                          puede_extraer_texto, busqueda_cronologica, puede_exportar)
VALUES 
(@usuario_id, @tomo_id, true, true, false, true, true, false);
*/