/**
 * Sistema de Tutorial Interactivo
 * Tutorial paso a paso para nuevos usuarios del sistema OCR FGJCDMX
 */

class TutorialInteractivo {
    constructor(pasos, nombreTutorial) {
        this.pasos = pasos;
        this.nombreTutorial = nombreTutorial;
        this.pasoActual = 0;
        this.overlay = null;
        this.modal = null;
        this.inicializar();
    }

    inicializar() {
        // Crear overlay oscuro
        this.overlay = document.createElement('div');
        this.overlay.id = 'tutorial-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            z-index: 9998;
            display: none;
        `;
        document.body.appendChild(this.overlay);

        // Crear modal del tutorial
        this.modal = document.createElement('div');
        this.modal.id = 'tutorial-modal';
        this.modal.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border-radius: 15px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            z-index: 9999;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            display: none;
        `;
        document.body.appendChild(this.modal);
    }

    iniciar() {
        const yaVisto = localStorage.getItem(`tutorial_${this.nombreTutorial}_visto`);
        
        if (!yaVisto) {
            this.mostrar();
        }
    }

    mostrar() {
        this.overlay.style.display = 'block';
        this.modal.style.display = 'block';
        this.mostrarPaso(0);
    }

    ocultar() {
        this.overlay.style.display = 'none';
        this.modal.style.display = 'none';
    }

    mostrarPaso(indice) {
        if (indice >= this.pasos.length) {
            this.finalizar();
            return;
        }

        this.pasoActual = indice;
        const paso = this.pasos[indice];

        // Resaltar elemento si existe
        if (paso.elemento) {
            this.resaltarElemento(paso.elemento);
        } else {
            this.limpiarResaltado();
        }

        // Contenido del modal
        this.modal.innerHTML = `
            <div class="tutorial-header" style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #1a365d; font-size: 24px;">
                        ${paso.icono} ${paso.titulo}
                    </h3>
                    <button onclick="tutorial.saltar()" style="
                        background: none;
                        border: none;
                        font-size: 24px;
                        cursor: pointer;
                        color: #999;
                    ">×</button>
                </div>
                <div style="margin-top: 10px; color: #666; font-size: 14px;">
                    Paso ${indice + 1} de ${this.pasos.length}
                </div>
                <div style="
                    width: 100%;
                    height: 4px;
                    background: #e0e0e0;
                    border-radius: 2px;
                    margin-top: 10px;
                    overflow: hidden;
                ">
                    <div style="
                        width: ${((indice + 1) / this.pasos.length) * 100}%;
                        height: 100%;
                        background: linear-gradient(135deg, #1a365d, #2c5aa0);
                        transition: width 0.3s ease;
                    "></div>
                </div>
            </div>

            <div class="tutorial-body" style="margin: 20px 0;">
                <p style="font-size: 16px; line-height: 1.6; color: #333;">
                    ${paso.descripcion}
                </p>
                ${paso.imagen ? `
                    <img src="${paso.imagen}" alt="${paso.titulo}" style="
                        max-width: 100%;
                        border-radius: 8px;
                        margin: 15px 0;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    ">
                ` : ''}
                ${paso.nota ? `
                    <div style="
                        background: #fff3cd;
                        border-left: 4px solid #ffc107;
                        padding: 12px;
                        margin-top: 15px;
                        border-radius: 4px;
                    ">
                        <strong>💡 Nota:</strong> ${paso.nota}
                    </div>
                ` : ''}
            </div>

            <div class="tutorial-footer" style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 25px;
            ">
                <button onclick="tutorial.anterior()" style="
                    padding: 10px 20px;
                    background: #6c757d;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    ${indice === 0 ? 'visibility: hidden;' : ''}
                ">
                    ← Anterior
                </button>
                <button onclick="tutorial.siguiente()" style="
                    padding: 10px 30px;
                    background: linear-gradient(135deg, #1a365d, #2c5aa0);
                    color: white;
                    border: none;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 14px;
                    font-weight: 600;
                ">
                    ${indice === this.pasos.length - 1 ? '¡Entendido! ✓' : 'Siguiente →'}
                </button>
            </div>
        `;
    }

    resaltarElemento(selector) {
        this.limpiarResaltado();
        
        const elemento = document.querySelector(selector);
        if (elemento) {
            // Hacer scroll al elemento
            elemento.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Agregar clase de resaltado
            elemento.classList.add('tutorial-resaltado');
            
            // Agregar estilos de resaltado
            const style = document.createElement('style');
            style.id = 'tutorial-highlight-style';
            style.textContent = `
                .tutorial-resaltado {
                    position: relative;
                    z-index: 9997 !important;
                    box-shadow: 0 0 0 4px rgba(52, 168, 83, 0.5), 
                                0 0 0 8px rgba(52, 168, 83, 0.3),
                                0 0 20px rgba(52, 168, 83, 0.4) !important;
                    animation: tutorial-pulse 2s infinite;
                }
                @keyframes tutorial-pulse {
                    0%, 100% { box-shadow: 0 0 0 4px rgba(52, 168, 83, 0.5), 
                                           0 0 0 8px rgba(52, 168, 83, 0.3),
                                           0 0 20px rgba(52, 168, 83, 0.4); }
                    50% { box-shadow: 0 0 0 4px rgba(52, 168, 83, 0.7), 
                                     0 0 0 8px rgba(52, 168, 83, 0.5),
                                     0 0 30px rgba(52, 168, 83, 0.6); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    limpiarResaltado() {
        document.querySelectorAll('.tutorial-resaltado').forEach(el => {
            el.classList.remove('tutorial-resaltado');
        });
        
        const style = document.getElementById('tutorial-highlight-style');
        if (style) {
            style.remove();
        }
    }

    siguiente() {
        this.mostrarPaso(this.pasoActual + 1);
    }

    anterior() {
        if (this.pasoActual > 0) {
            this.mostrarPaso(this.pasoActual - 1);
        }
    }

    saltar() {
        if (confirm('¿Seguro que quieres saltar el tutorial? Puedes verlo después desde el menú de ayuda.')) {
            this.finalizar();
        }
    }

    finalizar() {
        this.limpiarResaltado();
        this.ocultar();
        localStorage.setItem(`tutorial_${this.nombreTutorial}_visto`, 'true');
        
        // Mostrar mensaje de finalización
        if (this.pasoActual >= this.pasos.length - 1) {
            this.mostrarMensajeFinal();
        }
    }

    mostrarMensajeFinal() {
        const mensaje = document.createElement('div');
        mensaje.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 20px 30px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        mensaje.innerHTML = `
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-size: 24px;">✓</span>
                <div>
                    <strong>¡Tutorial completado!</strong>
                    <br>
                    <small>Puedes verlo nuevamente desde el menú de ayuda</small>
                </div>
            </div>
        `;
        
        document.body.appendChild(mensaje);
        
        setTimeout(() => {
            mensaje.remove();
        }, 5000);
    }

    reiniciar() {
        localStorage.removeItem(`tutorial_${this.nombreTutorial}_visto`);
        this.pasoActual = 0;
        this.iniciar();
    }
}

// Variable global para acceder al tutorial
let tutorial = null;
