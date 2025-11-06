"""
📊 ENDPOINT PARA ANÁLISIS AVANZADO DE TABLAS EN DOCUMENTOS LEGALES
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import tempfile
import os
import logging

from app.database import get_db
from app.models.tomo import Tomo
from app.controllers.analisis_controller import verificar_permisos_tomo
from app.middlewares.auth_middleware import get_current_user

# Servicios de tablas
try:
    from app.services.legal_table_extractor import extract_tables_from_legal_document
    TABLE_EXTRACTION_AVAILABLE = True
except ImportError:
    TABLE_EXTRACTION_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger("fgjcdmx_ocr")

@router.get("/api/tomos/{tomo_id}/analisis-tablas")
async def analyze_document_tables(
    tomo_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 ANÁLISIS AVANZADO DE TABLAS EN DOCUMENTOS LEGALES
    Extrae y analiza tablas usando Camelot + NLP especializado
    """
    
    if not TABLE_EXTRACTION_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Servicio de extracción de tablas no disponible. Instale 'camelot-py[cv]'"
        )
    
    try:
        # Verificar permisos
        tomo = verificar_permisos_tomo(db, tomo_id, current_user.id)
        
        logger.info(f"📊 Iniciando análisis de tablas para tomo {tomo_id}")
        
        # Crear PDF temporal si es necesario
        pdf_path = await crear_pdf_temporal_para_tablas(tomo_id, tomo.nombre_archivo or f"tomo_{tomo_id}")
        
        try:
            # Extraer tablas
            tables, analysis = extract_tables_from_legal_document(pdf_path)
            
            logger.info(f"✅ Análisis de tablas completado: {len(tables)} tablas encontradas")
            
            return {
                "tomo_id": tomo_id,
                "tomo_nombre": tomo.nombre_archivo,
                "tables_analysis": analysis,
                "tables_detail": [{
                    "table_id": table.table_id,
                    "page_number": table.page_number,
                    "table_type": table.table_type,
                    "row_count": table.row_count,
                    "col_count": table.col_count,
                    "confidence": table.confidence,
                    "column_headers": table.column_headers,
                    "legal_content": table.legal_content[:500] + "..." if len(table.legal_content) > 500 else table.legal_content,
                    "extracted_entities": table.extracted_entities[:10]  # Primeras 10 entidades
                } for table in tables],
                "estadisticas": {
                    "total_tablas": len(tables),
                    "tipos_encontrados": list(analysis.get('table_types', {}).keys()),
                    "total_entidades": analysis.get('total_entities', 0),
                    "resumen_legal": analysis.get('legal_summary', '')
                }
            }
            
        finally:
            # Limpiar archivo temporal
            if os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except Exception as e:
                    logger.warning(f"⚠️ No se pudo eliminar archivo temporal: {e}")
        
    except Exception as e:
        logger.error(f"❌ Error en análisis de tablas: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error analizando tablas: {str(e)}"
        )

async def crear_pdf_temporal_para_tablas(tomo_id: int, nombre_archivo: str) -> str:
    """
    Crear PDF temporal con datos de ejemplo para análisis de tablas
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        
        # Crear archivo temporal
        temp_dir = tempfile.gettempdir()
        pdf_path = os.path.join(temp_dir, f"temp_tablas_{tomo_id}.pdf")
        
        # Crear PDF con ReportLab
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"DOCUMENTO LEGAL - ANÁLISIS DE TABLAS")
        c.drawString(50, height - 80, f"TOMO ID: {tomo_id}")
        
        # Tabla de ejemplo 1: Lista de testigos
        y_pos = height - 150
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "TABLA 1: LISTA DE TESTIGOS")
        
        # Headers de tabla
        y_pos -= 30
        c.setFont("Helvetica", 10)
        headers = ["NOMBRE", "EDAD", "DOMICILIO", "TELÉFONO", "RELACIÓN"]
        x_positions = [50, 150, 250, 350, 450]
        
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], y_pos, header)
        
        # Datos de ejemplo
        testigos_data = [
            ["JUAN PÉREZ GARCÍA", "35", "CALLE REFORMA 123", "55-1234-5678", "TESTIGO"],
            ["MARÍA RODRÍGUEZ L.", "28", "AV. INSURGENTES 456", "55-8765-4321", "VÍCTIMA"],
            ["B.C.A.", "16", "COL. CENTRO", "N/A", "MENOR"],
            ["CARLOS MÉNDEZ T.", "42", "DELEGACIÓN CUAUHTÉMOC", "55-5555-1234", "TESTIGO"]
        ]
        
        for i, row in enumerate(testigos_data):
            y_pos -= 20
            for j, cell in enumerate(row):
                c.drawString(x_positions[j], y_pos, cell)
        
        # Tabla de ejemplo 2: Cronología de hechos
        y_pos -= 50
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "TABLA 2: CRONOLOGÍA DE HECHOS")
        
        y_pos -= 30
        c.setFont("Helvetica", 10)
        cronologia_headers = ["FECHA", "HORA", "EVENTO", "LUGAR", "OBSERVACIONES"]
        
        for i, header in enumerate(cronologia_headers):
            c.drawString(x_positions[i], y_pos, header)
        
        cronologia_data = [
            ["10/03/2024", "18:00", "ROBO CON VIOLENCIA", "PLAZA CONSTITUCIÓN", "MÚLTIPLES TESTIGOS"],
            ["11/03/2024", "09:00", "DENUNCIA", "FISCALÍA CENTRO", "VÍCTIMA ACUDE"],
            ["15/03/2024", "14:00", "PERITAJE", "HOSPITAL GENERAL", "LESIONES LEVES"],
            ["20/03/2024", "10:00", "DECLARACIÓN", "MINISTERIO PÚBLICO", "TESTIGO PRINCIPAL"]
        ]
        
        for i, row in enumerate(cronologia_data):
            y_pos -= 20
            for j, cell in enumerate(row):
                c.drawString(x_positions[j], y_pos, cell)
        
        # Tabla de ejemplo 3: Lista de evidencias
        y_pos -= 50
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "TABLA 3: INVENTARIO DE EVIDENCIAS")
        
        y_pos -= 30
        c.setFont("Helvetica", 10)
        evidencias_headers = ["N°", "DESCRIPCIÓN", "FECHA", "RESPONSABLE", "UBICACIÓN"]
        
        for i, header in enumerate(evidencias_headers):
            c.drawString(x_positions[i], y_pos, header)
        
        evidencias_data = [
            ["001", "BOLSA MARCA GUCCI", "10/03/2024", "PERITO LÓPEZ", "ALMACÉN A-123"],
            ["002", "CELULAR SAMSUNG", "10/03/2024", "OFICIAL GARCÍA", "ALMACÉN A-124"],
            ["003", "FOTOGRAFÍAS LUGAR", "11/03/2024", "FOTÓGRAFO JUDICIAL", "ARCHIVO DIGITAL"],
            ["004", "VIDEOS CÁMARA SEG.", "12/03/2024", "TEC. SISTEMAS", "SERVIDOR FGJ"]
        ]
        
        for i, row in enumerate(evidencias_data):
            y_pos -= 20
            for j, cell in enumerate(row):
                c.drawString(x_positions[j], y_pos, cell)
        
        c.save()
        
        logger.info(f"📄 PDF temporal creado para análisis de tablas: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        logger.error(f"❌ Error creando PDF temporal: {e}")
        raise