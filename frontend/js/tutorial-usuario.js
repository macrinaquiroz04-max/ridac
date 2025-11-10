/**
 * Tutorial para Usuarios Regulares
 * Guía paso a paso para usar el Sistema OCR FGJCDMX
 */

const tutorialUsuario = [
    {
        icono: '👋',
        titulo: '¡Bienvenido al Sistema OCR!',
        descripcion: `
            <strong>¡Hola!</strong><br><br>
            Este es el <strong>Sistema OCR de la Fiscalía General de Justicia de la CDMX</strong>.<br><br>
            Te permite consultar, buscar y exportar documentos de las carpetas de investigación 
            a las que tienes acceso.<br><br>
            
            <strong>Importante:</strong> El sistema <strong>NO es perfecto</strong>. El OCR puede tener 
            errores en el reconocimiento de texto, especialmente en documentos escaneados de baja calidad.
        `,
        nota: 'Este tutorial solo aparece una vez. Puedes verlo nuevamente desde el menú de ayuda (❓)'
    },
    {
        icono: '📚',
        titulo: 'Tus Tomos Disponibles',
        elemento: '#listado-tomos',
        descripcion: `
            Aquí ves <strong>todos los tomos a los que tienes acceso</strong>.<br><br>
            
            <strong>Información de cada tomo:</strong><br>
            • <strong>Nombre</strong>: Identificador del tomo<br>
            • <strong>Carpeta</strong>: Carpeta de investigación a la que pertenece<br>
            • <strong>Páginas</strong>: Número total de páginas<br>
            • <strong>Estado OCR</strong>: Si el texto ya fue procesado<br><br>
            
            <strong>Íconos de acciones:</strong><br>
            • 👁️ Ver: Abrir el visor de PDF<br>
            • 🔍 Buscar: Buscar texto en el tomo<br>
            • 📥 Exportar: Descargar el PDF original
        `,
        nota: 'Solo verás los tomos que el administrador te haya autorizado'
    },
    {
        icono: '👁️',
        titulo: 'Visor de Documentos',
        descripcion: `
            El <strong>Visor de PDF</strong> te permite leer los tomos cómodamente.<br><br>
            
            <strong>Funciones disponibles:</strong><br>
            • <strong>Navegación</strong>: Páginas anterior/siguiente<br>
            • <strong>Zoom</strong>: Acercar o alejar el documento<br>
            • <strong>Selección Inteligente</strong>: Selecciona texto con el mouse y cópialo<br>
            • <strong>Vista completa</strong>: Pantalla completa para mejor lectura<br><br>
            
            <strong>Nota importante:</strong> La selección de texto funciona mejor en documentos 
            con OCR de buena calidad.
        `,
        nota: 'Haz clic en el icono 👁️ de cualquier tomo para abrir el visor'
    },
    {
        icono: '🔍',
        titulo: 'Búsqueda de Texto',
        descripcion: `
            Puedes <strong>buscar palabras o frases</strong> dentro de los tomos.<br><br>
            
            <strong>Cómo buscar:</strong><br>
            1. Haz clic en el icono <strong>🔍 BUSCAR</strong> del tomo<br>
            2. Escribe la palabra o frase que buscas<br>
            3. El sistema mostrará todas las coincidencias<br>
            4. Haz clic en un resultado para ir a esa página<br><br>
            
            <strong>Tipos de búsqueda:</strong><br>
            • <strong>Simple</strong>: Busca palabras exactas<br>
            • <strong>Avanzada</strong>: Usa operadores (AND, OR, NOT)<br>
            • <strong>Semántica</strong>: Busca por conceptos similares
        `,
        nota: 'La búsqueda semántica es más inteligente pero puede tardar más tiempo'
    },
    {
        icono: '🧠',
        titulo: 'Búsqueda Semántica Avanzada',
        elemento: 'button[onclick*="semantica"]',
        descripcion: `
            La <strong>búsqueda semántica</strong> es más poderosa que la búsqueda normal.<br><br>
            
            <strong>¿Qué hace diferente?</strong><br>
            • Encuentra conceptos similares, no solo palabras exactas<br>
            • Entiende sinónimos y términos relacionados<br>
            • Busca en TODOS tus tomos a la vez<br><br>
            
            <strong>Ejemplo:</strong><br>
            Si buscas "vehículo", también encontrará: auto, carro, automóvil, camioneta, etc.<br><br>
            
            <strong>Limitaciones:</strong><br>
            • Puede tardar más tiempo<br>
            • Depende de la calidad del OCR<br>
            • No siempre es 100% precisa
        `,
        nota: 'Úsala cuando la búsqueda simple no encuentre lo que necesitas'
    },
    {
        icono: '📥',
        titulo: 'Exportar Documentos',
        descripcion: `
            Puedes <strong>descargar los PDF originales</strong> si necesitas trabajar offline.<br><br>
            
            <strong>Cómo exportar:</strong><br>
            1. Haz clic en el icono <strong>📥 EXPORTAR</strong> del tomo<br>
            2. El archivo PDF se descargará automáticamente<br>
            3. Guárdalo en tu computadora<br><br>
            
            <strong>Importante:</strong><br>
            • Solo puedes exportar si el admin te dio ese permiso<br>
            • Se registra en auditoría cada vez que exportas<br>
            • El archivo es el PDF original, sin modificaciones
        `,
        nota: 'Si no ves el botón EXPORTAR, es porque no tienes ese permiso en ese tomo'
    },
    {
        icono: '📊',
        titulo: 'Análisis Jurídico Avanzado',
        descripcion: `
            El botón <strong>"📊 Ver Análisis"</strong> abre herramientas avanzadas de análisis.<br><br>
            
            <strong>¿Qué puedes hacer?</strong><br>
            • <strong>Línea de Tiempo</strong>: Visualiza eventos cronológicamente<br>
            • <strong>Mapa de Relaciones</strong>: Personas y conexiones identificadas<br>
            • <strong>Lugares Importantes</strong>: Ubicaciones mencionadas en documentos<br>
            • <strong>Entidades Legales</strong>: Nombres, fechas, lugares extraídos<br>
            • <strong>Alertas</strong>: Inconsistencias o patrones detectados<br><br>
            
            <strong>Casos de uso:</strong><br>
            • Identificar conexiones entre personas<br>
            • Detectar inconsistencias en testimonios<br>
            • Construir cronología de eventos<br>
            • Visualizar ubicaciones relevantes en mapas<br><br>
            
            <strong>Nota:</strong> Esta función usa IA para extraer información. 
            Siempre <strong>verifica los datos originales</strong> en los documentos.
        `,
        nota: 'El botón "Ver Análisis" aparece en cada grupo de tomos de una carpeta'
    },
    {
        icono: '🎯',
        titulo: 'Consejos Finales',
        descripcion: `
            <strong>¡Ya sabes usar el sistema!</strong><br><br>
            
            <strong>Consejos útiles:</strong><br>
            • Usa <strong>búsqueda simple</strong> para consultas rápidas<br>
            • Usa <strong>búsqueda semántica</strong> cuando no encuentres resultados<br>
            • El <strong>Análisis Jurídico</strong> te ayuda a encontrar patrones y conexiones<br>
            • Si el OCR tiene errores, intenta buscar con sinónimos<br>
            • Puedes tener varios tomos abiertos en pestañas diferentes<br>
            • La <strong>Selección Inteligente</strong> te ayuda a copiar texto del PDF<br><br>
            
            <strong>Recuerda:</strong><br>
            El sistema no es perfecto, pero está diseñado para ahorrarte tiempo 
            al buscar información en carpetas de investigación.<br><br>
            
            <strong>Si encuentras problemas, reporta con el administrador.</strong>
        `
    }
];

// Inicializar tutorial cuando cargue la página
document.addEventListener('DOMContentLoaded', function() {
    // Esperar 1 segundo para que la página cargue completamente
    setTimeout(() => {
        tutorial = new TutorialInteractivo(tutorialUsuario, 'dashboard_usuario');
        tutorial.iniciar();
    }, 1000);
});

// Función para reiniciar el tutorial desde el menú de ayuda
function reiniciarTutorial() {
    if (tutorial) {
        tutorial.reiniciar();
    }
}
