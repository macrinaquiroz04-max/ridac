/**
 * Tutorial para Administradores
 * Guía paso a paso para administrar el Sistema OCR FGJCDMX
 */

const tutorialAdmin = [
    {
        icono: '🏛️',
        titulo: '¡Bienvenido al Sistema OCR!',
        descripcion: `
            <strong>¡Hola, Administrador!</strong><br><br>
            Este es el <strong>Sistema OCR de la Fiscalía General de Justicia de la CDMX</strong>.<br><br>
            Te guiaré en 6 pasos rápidos para que puedas administrar el sistema como un experto.
            <br><br>
            <strong>El sistema NO es perfecto</strong>, pero está diseñado para facilitar tu trabajo diario.
        `,
        nota: 'Este tutorial solo aparece una vez. Puedes verlo nuevamente desde el menú de ayuda (❓)'
    },
    {
        icono: '👥',
        titulo: 'Gestionar Usuarios',
        elemento: '#btnUsuarios',
        descripcion: `
            El primer paso es <strong>crear y gestionar usuarios</strong>.<br><br>
            
            <strong>Pasos para crear un usuario:</strong><br>
            1. Haz clic en el botón <strong>"👥 Gestionar Usuarios"</strong><br>
            2. Clic en <strong>"+ Nuevo Usuario"</strong><br>
            3. Completa el formulario (nombre, email, rol)<br>
            4. El sistema genera una contraseña temporal<br>
            5. Comparte las credenciales con el usuario
        `,
        nota: 'Los usuarios pueden cambiar su contraseña temporal la primera vez que ingresen'
    },
    {
        icono: '📁',
        titulo: 'Subir Carpetas y Tomos',
        elemento: 'button[onclick*="carpetas"]',
        descripcion: `
            Para que los usuarios puedan trabajar, necesitas <strong>subir las carpetas investigación</strong>.<br><br>
            
            <strong>Proceso de carga:</strong><br>
            1. Haz clic en <strong>"📁 Gestionar Carpetas"</strong><br>
            2. Crea una nueva carpeta de investigación<br>
            3. Sube los tomos en formato PDF<br>
            4. El sistema procesará automáticamente el OCR<br>
            5. Espera a que el estado cambie a <strong>"Completado"</strong>
        `,
        nota: 'El procesamiento OCR puede tardar varios minutos dependiendo del tamaño del PDF'
    },
    {
        icono: '🔐',
        titulo: 'Asignar Permisos a Usuarios',
        descripcion: `
            <strong>¡Importante!</strong> Los usuarios NO verán ningún tomo hasta que les asignes permisos.<br><br>
            
            <strong>Cómo asignar permisos:</strong><br>
            1. Ve al menú lateral → <strong>"Gestión de Permisos"</strong><br>
            2. Selecciona un usuario de la lista<br>
            3. Busca la carpeta que quieres compartir<br>
            4. Usa los botones de acceso rápido:<br>
               • <strong>Verde</strong>: Acceso completo (ver + buscar + exportar)<br>
               • <strong>Amarillo</strong>: Solo visualización<br>
               • <strong>Rojo</strong>: Quitar todos los permisos
        `,
        nota: 'Los cambios en permisos se reflejan instantáneamente en el dashboard del usuario'
    },
    {
        icono: '🔍',
        titulo: 'Auditoría del Sistema',
        elemento: '#btnAuditoria',
        descripcion: `
            Puedes <strong>monitorear toda la actividad</strong> del sistema desde la auditoría.<br><br>
            
            <strong>Qué puedes ver:</strong><br>
            • Quién accedió a qué tomos y cuándo<br>
            • Búsquedas realizadas por cada usuario<br>
            • Exportaciones de documentos<br>
            • Cambios en permisos<br>
            • Usuarios activos en tiempo real
        `,
        nota: 'Útil para verificar que los usuarios están usando correctamente el sistema'
    },
    {
        icono: '✅',
        titulo: '¡Listo para Empezar!',
        descripcion: `
            <strong>Ya conoces lo básico del sistema.</strong><br><br>
            
            <strong>Resumen rápido:</strong><br>
            1. ✅ Crear usuarios<br>
            2. ✅ Subir carpetas y tomos<br>
            3. ✅ Asignar permisos<br>
            4. ✅ Monitorear con auditoría<br><br>
            
            <strong>Recuerda:</strong> El sistema no es perfecto, pero te ayudará a:<br>
            • Organizar carpetas de investigación<br>
            • Controlar quién ve qué documentos<br>
            • Buscar información rápidamente<br>
            • Mantener un registro de accesos<br><br>
            
            <strong>Si tienes dudas, contacta al soporte técnico.</strong>
        `
    }
];

// Inicializar tutorial cuando cargue la página
document.addEventListener('DOMContentLoaded', function() {
    // Esperar 1 segundo para que la página cargue completamente
    setTimeout(() => {
        tutorial = new TutorialInteractivo(tutorialAdmin, 'dashboard_admin');
        tutorial.iniciar();
    }, 1000);
});

// Función para reiniciar el tutorial desde el menú de ayuda
function reiniciarTutorial() {
    if (tutorial) {
        tutorial.reiniciar();
    }
}
