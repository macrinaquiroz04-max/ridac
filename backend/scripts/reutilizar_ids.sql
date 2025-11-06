-- Script para permitir reutilización de IDs eliminados
-- Esto crea una función que busca el primer ID disponible

-- Función para obtener el próximo ID disponible (reutilizando huecos)
CREATE OR REPLACE FUNCTION obtener_proximo_id_usuario()
RETURNS INTEGER AS $$
DECLARE
    next_id INTEGER;
BEGIN
    -- Buscar el primer hueco en los IDs
    SELECT COALESCE(MIN(t1.id + 1), 1) INTO next_id
    FROM usuarios t1
    WHERE NOT EXISTS (
        SELECT 1 FROM usuarios t2 WHERE t2.id = t1.id + 1
    );
    
    -- Si no hay huecos, usar el siguiente después del máximo
    IF next_id IS NULL OR next_id <= (SELECT COALESCE(MAX(id), 0) FROM usuarios) THEN
        SELECT COALESCE(MIN(id + 1), 1) INTO next_id
        FROM usuarios
        WHERE id + 1 NOT IN (SELECT id FROM usuarios);
    END IF;
    
    -- Si aún no hay resultado, usar max + 1
    IF next_id IS NULL THEN
        SELECT COALESCE(MAX(id), 0) + 1 INTO next_id FROM usuarios;
    END IF;
    
    RETURN next_id;
END;
$$ LANGUAGE plpgsql;

-- Modificar la columna ID para no usar secuencia automática
ALTER TABLE usuarios ALTER COLUMN id DROP DEFAULT;

-- Comentario explicativo
COMMENT ON FUNCTION obtener_proximo_id_usuario() IS 
'Devuelve el siguiente ID disponible, reutilizando IDs de registros eliminados';

-- Probar la función
SELECT obtener_proximo_id_usuario() as proximo_id_disponible;
