"""
📊 SERVICIO DE EXTRACCIÓN DE TABLAS EN DOCUMENTOS LEGALES
Camelot + análisis especializado para tablas de fiscalía
"""

import warnings
import camelot
import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import tempfile
import os

# Suprimir advertencias de camelot/matplotlib
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")

logger = logging.getLogger("fgjcdmx_ocr")

@dataclass
class LegalTable:
    """Tabla extraída de documento legal"""
    table_id: int
    page_number: int
    table_type: str
    data: pd.DataFrame
    confidence: float
    column_headers: List[str]
    row_count: int
    col_count: int
    legal_content: str
    extracted_entities: List[Dict]

class LegalTableExtractor:
    """Extractor especializado de tablas en documentos legales"""
    
    def __init__(self):
        self.table_types = {
            'ACTAS_AUDIENCIA': {
                'keywords': ['ACTA', 'AUDIENCIA', 'FECHA', 'HORA', 'PARTICIPANTES'],
                'expected_cols': ['fecha', 'hora', 'tipo', 'participantes', 'observaciones']
            },
            'LISTA_EVIDENCIAS': {
                'keywords': ['EVIDENCIA', 'INDICIO', 'NÚMERO', 'DESCRIPCIÓN', 'CADENA'],
                'expected_cols': ['numero', 'descripcion', 'fecha', 'responsable', 'ubicacion']
            },
            'CRONOLOGIA_HECHOS': {
                'keywords': ['CRONOLOGÍA', 'HECHOS', 'FECHA', 'EVENTO', 'LUGAR'],
                'expected_cols': ['fecha', 'hora', 'evento', 'lugar', 'testigos']
            },
            'LISTA_TESTIGOS': {
                'keywords': ['TESTIGO', 'DECLARANTE', 'NOMBRE', 'DOMICILIO'],
                'expected_cols': ['nombre', 'edad', 'domicilio', 'telefono', 'relacion']
            },
            'DILIGENCIAS': {
                'keywords': ['DILIGENCIA', 'OFICIO', 'FECHA', 'DESTINATARIO'],
                'expected_cols': ['fecha', 'tipo', 'destinatario', 'asunto', 'estatus']
            },
            'INVENTARIO_BIENES': {
                'keywords': ['INVENTARIO', 'BIEN', 'DESCRIPCIÓN', 'VALOR'],
                'expected_cols': ['descripcion', 'valor', 'ubicacion', 'estado', 'observaciones']
            }
        }
    
    def extract_tables_from_pdf(self, pdf_path: str) -> List[LegalTable]:
        """
        Extraer todas las tablas de un PDF legal
        """
        legal_tables = []
        
        try:
            # Extraer tablas usando Camelot
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            if tables.n == 0:
                # Intentar con método stream si lattice no encuentra tablas
                tables = camelot.read_pdf(pdf_path, pages='all', flavor='stream')
            
            logger.info(f"📊 Encontradas {tables.n} tablas en el documento")
            
            for i, table in enumerate(tables):
                legal_table = self._process_table(table, i + 1)
                if legal_table:
                    legal_tables.append(legal_table)
                    
        except Exception as e:
            logger.error(f"Error extrayendo tablas: {e}")
            # Fallback: intentar extracción básica
            return self._fallback_table_extraction(pdf_path)
        
        return legal_tables
    
    def _process_table(self, camelot_table, table_id: int) -> Optional[LegalTable]:
        """
        Procesar una tabla individual de Camelot
        """
        try:
            df = camelot_table.df
            page_num = camelot_table.page
            
            # Limpiar tabla
            df = self._clean_table_data(df)
            
            if df.empty or len(df.columns) < 2:
                return None
            
            # Detectar tipo de tabla
            table_type = self._detect_table_type(df)
            
            # Extraer entidades legales de la tabla
            entities = self._extract_entities_from_table(df, table_type)
            
            # Generar contenido textual de la tabla
            legal_content = self._table_to_legal_text(df, table_type)
            
            return LegalTable(
                table_id=table_id,
                page_number=page_num,
                table_type=table_type,
                data=df,
                confidence=camelot_table.accuracy if hasattr(camelot_table, 'accuracy') else 0.8,
                column_headers=list(df.columns),
                row_count=len(df),
                col_count=len(df.columns),
                legal_content=legal_content,
                extracted_entities=entities
            )
            
        except Exception as e:
            logger.error(f"Error procesando tabla {table_id}: {e}")
            return None
    
    def _clean_table_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Limpiar datos de tabla extraída
        """
        # Eliminar filas y columnas completamente vacías
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Limpiar espacios extra
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()
                df[col] = df[col].replace('', pd.NA)
        
        # Usar primera fila como headers si parece apropiado
        first_row = df.iloc[0] if len(df) > 0 else None
        if first_row is not None and self._looks_like_headers(first_row):
            df.columns = first_row
            df = df.drop(df.index[0]).reset_index(drop=True)
        
        return df
    
    def _looks_like_headers(self, row: pd.Series) -> bool:
        """
        Determinar si una fila parece contener headers
        """
        text_content = ' '.join(str(val) for val in row if pd.notna(val)).upper()
        
        header_indicators = [
            'FECHA', 'NOMBRE', 'DESCRIPCIÓN', 'TIPO', 'NÚMERO', 'HORA',
            'LUGAR', 'DOMICILIO', 'TELÉFONO', 'OBSERVACIONES', 'ESTATUS',
            'VALOR', 'CANTIDAD', 'PARTICIPANTE', 'TESTIGO', 'EVIDENCIA'
        ]
        
        matches = sum(1 for indicator in header_indicators if indicator in text_content)
        return matches >= 2
    
    def _detect_table_type(self, df: pd.DataFrame) -> str:
        """
        Detectar el tipo de tabla legal basado en contenido
        """
        # Convertir toda la tabla a texto para análisis
        table_text = df.to_string().upper()
        
        best_match = 'TABLA_GENERAL'
        best_score = 0
        
        for table_type, config in self.table_types.items():
            score = 0
            for keyword in config['keywords']:
                if keyword in table_text:
                    score += 1
            
            # Normalizar score por número de keywords
            normalized_score = score / len(config['keywords'])
            
            if normalized_score > best_score:
                best_score = normalized_score
                best_match = table_type
        
        return best_match if best_score > 0.3 else 'TABLA_GENERAL'
    
    def _extract_entities_from_table(self, df: pd.DataFrame, table_type: str) -> List[Dict]:
        """
        Extraer entidades legales específicas de la tabla
        """
        entities = []
        
        try:
            for idx, row in df.iterrows():
                row_entities = []
                
                for col, value in row.items():
                    if pd.isna(value):
                        continue
                    
                    value_str = str(value).strip()
                    
                    # Detectar fechas
                    if self._is_date(value_str):
                        row_entities.append({
                            'type': 'FECHA',
                            'value': value_str,
                            'column': col,
                            'row': idx
                        })
                    
                    # Detectar nombres
                    elif self._is_person_name(value_str):
                        # Proteger menores
                        if self._is_minor_protected(value_str):
                            value_str = "[MENOR PROTEGIDO]"
                        
                        row_entities.append({
                            'type': 'NOMBRE',
                            'value': value_str,
                            'column': col,
                            'row': idx
                        })
                    
                    # Detectar direcciones
                    elif self._is_address(value_str):
                        row_entities.append({
                            'type': 'DIRECCION',
                            'value': value_str,
                            'column': col,
                            'row': idx
                        })
                    
                    # Detectar teléfonos
                    elif self._is_phone_number(value_str):
                        row_entities.append({
                            'type': 'TELEFONO',
                            'value': value_str,
                            'column': col,
                            'row': idx
                        })
                
                if row_entities:
                    entities.extend(row_entities)
                    
        except Exception as e:
            logger.error(f"Error extrayendo entidades de tabla: {e}")
        
        return entities
    
    def _is_date(self, text: str) -> bool:
        """Detectar si el texto es una fecha"""
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
    
    def _is_person_name(self, text: str) -> bool:
        """Detectar si el texto es un nombre de persona"""
        if len(text) < 3 or len(text) > 100:
            return False
        
        # Patrón de nombre completo
        name_pattern = r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)+$'
        
        # O patrón de iniciales (menores protegidos)
        initials_pattern = r'^[A-Z]\.([A-Z]\.)+$'
        
        return bool(re.match(name_pattern, text) or re.match(initials_pattern, text))
    
    def _is_minor_protected(self, text: str) -> bool:
        """Detectar si es un menor protegido"""
        return bool(re.match(r'^[A-Z]\.([A-Z]\.)+$', text))
    
    def _is_address(self, text: str) -> bool:
        """Detectar si el texto es una dirección"""
        address_indicators = [
            r'\b(calle|av\.|avenida|blvd\.|boulevard)\s+',
            r'\b(col\.|colonia)\s+',
            r'\b(delegación|alcaldía)\s+',
            r'\bc\.p\.\s*\d{5}\b'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in address_indicators)
    
    def _is_phone_number(self, text: str) -> bool:
        """Detectar si el texto es un número de teléfono"""
        phone_patterns = [
            r'\b\d{2}[-\s]?\d{4}[-\s]?\d{4}\b',  # 55-1234-5678
            r'\b\d{10}\b'  # 5512345678
        ]
        
        return any(re.search(pattern, text) for pattern in phone_patterns)
    
    def _table_to_legal_text(self, df: pd.DataFrame, table_type: str) -> str:
        """
        Convertir tabla a texto legal estructurado
        """
        try:
            text_parts = [f"TABLA DE TIPO: {table_type}"]
            text_parts.append(f"REGISTROS: {len(df)}")
            text_parts.append("")
            
            for idx, row in df.iterrows():
                row_text = f"REGISTRO {idx + 1}:"
                for col, value in row.items():
                    if pd.notna(value) and str(value).strip():
                        row_text += f" {col}: {value};"
                text_parts.append(row_text)
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error convirtiendo tabla a texto: {e}")
            return f"TABLA DE TIPO: {table_type} (Error en conversión)"
    
    def _fallback_table_extraction(self, pdf_path: str) -> List[LegalTable]:
        """
        Extracción de tablas de fallback usando pandas
        """
        try:
            # Intentar con pandas como fallback
            dfs = pd.read_pdf(pdf_path, pages='all', multiple_tables=True)
            
            legal_tables = []
            for i, df in enumerate(dfs):
                if not df.empty:
                    legal_table = LegalTable(
                        table_id=i + 1,
                        page_number=1,  # No sabemos la página exacta
                        table_type='TABLA_GENERAL',
                        data=df,
                        confidence=0.6,  # Confianza baja para fallback
                        column_headers=list(df.columns),
                        row_count=len(df),
                        col_count=len(df.columns),
                        legal_content=self._table_to_legal_text(df, 'TABLA_GENERAL'),
                        extracted_entities=[]
                    )
                    legal_tables.append(legal_table)
            
            return legal_tables
            
        except Exception as e:
            logger.error(f"Error en extracción fallback: {e}")
            return []
    
    def analyze_tables_legal_context(self, tables: List[LegalTable]) -> Dict[str, Any]:
        """
        Análizar contexto legal de todas las tablas extraídas
        """
        if not tables:
            return {
                'tables_found': 0,
                'table_types': {},
                'total_entities': 0,
                'legal_summary': 'No se encontraron tablas en el documento'
            }
        
        # Estadísticas generales
        table_types = {}
        total_entities = 0
        
        for table in tables:
            table_type = table.table_type
            table_types[table_type] = table_types.get(table_type, 0) + 1
            total_entities += len(table.extracted_entities)
        
        # Generar resumen legal
        summary_parts = []
        
        if 'ACTAS_AUDIENCIA' in table_types:
            summary_parts.append(f"Documento contiene {table_types['ACTAS_AUDIENCIA']} actas de audiencia")
        
        if 'LISTA_EVIDENCIAS' in table_types:
            summary_parts.append(f"Se identificaron {table_types['LISTA_EVIDENCIAS']} listas de evidencias")
        
        if 'CRONOLOGIA_HECHOS' in table_types:
            summary_parts.append("Incluye cronología de hechos")
        
        if 'LISTA_TESTIGOS' in table_types:
            summary_parts.append(f"Contiene {table_types['LISTA_TESTIGOS']} listas de testigos")
        
        legal_summary = ". ".join(summary_parts) if summary_parts else "Documento con tablas de información general"
        
        return {
            'tables_found': len(tables),
            'table_types': table_types,
            'total_entities': total_entities,
            'legal_summary': legal_summary,
            'tables_detail': [{
                'id': t.table_id,
                'type': t.table_type,
                'page': t.page_number,
                'rows': t.row_count,
                'cols': t.col_count,
                'confidence': t.confidence,
                'entities_count': len(t.extracted_entities)
            } for t in tables]
        }

# Instancia global del extractor
legal_table_extractor = LegalTableExtractor()

def extract_tables_from_legal_document(pdf_path: str) -> Tuple[List[LegalTable], Dict[str, Any]]:
    """
    Función de integración para extraer tablas de documento legal
    """
    tables = legal_table_extractor.extract_tables_from_pdf(pdf_path)
    analysis = legal_table_extractor.analyze_tables_legal_context(tables)
    
    return tables, analysis