from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.extraccion import (
    ExtraccionTomo, DiligenciaTomo, PersonaMencionada,
    Declaracion, AlertaInactividad
)
from app.models.tomo import Tomo, ContenidoOCR
import re

class ExtractorService:
    def __init__(self, db: Session):
        self.db = db

    def extraer_diligencias(self, tomo_id: int, texto: str, pagina: int) -> List[Dict]:
        """Extrae información sobre diligencias del texto"""
        # Patrones para identificar diferentes tipos de diligencias
        patrones = {
            'informe_pericial': r'INFORME\s+PERICIAL.*?FECHA[:\s]+(\d{1,2}/\d{1,2}/\d{4})',
            'comparecencia': r'COMPARECE.*?(\d{1,2}/\d{1,2}/\d{4})',
            'oficio': r'OFICIO\s+(?:No\.|NUM\.|NÚMERO:?\s+)?([A-Z0-9-]+/\d{4})',
        }

        diligencias = []
        for tipo, patron in patrones.items():
            matches = re.finditer(patron, texto, re.IGNORECASE)
            for match in matches:
                diligencia = DiligenciaTomo(
                    tomo_id=tomo_id,
                    pagina=pagina,
                    tipo_diligencia=tipo,
                    fecha=self._parsear_fecha(match.group(1)),
                    contenido=match.group(0)
                )
                self.db.add(diligencia)
                diligencias.append(diligencia)

        return diligencias

    def extraer_personas(self, tomo_id: int, texto: str) -> List[Dict]:
        """Extrae información sobre personas mencionadas"""
        # Patrones para identificar personas y sus datos
        patron_persona = r'(?:LIC\.|C\.|LICENCIADO|PERITO|TESTIGO|DECLARANTE)\s+([A-ZÁÉÍÓÚÑ\s]+)'
        patron_telefono = r'(?:TEL(?:É|E)FONO|TEL\.?|CEL\.?)?\s*(\d{10}|\d{8})'
        patron_direccion = r'(?:DOMICILIO|DIRECCIÓN|UBICADO\s+EN)[:\s]+([^\.]+)'

        personas = []
        for match in re.finditer(patron_persona, texto, re.IGNORECASE):
            nombre = match.group(1).strip()
            # Buscar teléfono y dirección cercanos
            contexto = texto[max(0, match.start()-200):match.end()+200]
            telefono = re.search(patron_telefono, contexto)
            direccion = re.search(patron_direccion, contexto)

            persona = PersonaMencionada(
                tomo_id=tomo_id,
                nombre=nombre,
                telefono=telefono.group(1) if telefono else None,
                direccion=direccion.group(1) if direccion else None
            )
            self.db.add(persona)
            personas.append(persona)

        return personas

    def verificar_inactividad(self, tomo_id: int, umbral_dias: int = 180) -> List[AlertaInactividad]:
        """Verifica períodos de inactividad en las diligencias"""
        diligencias = self.db.query(DiligenciaTomo).filter(
            DiligenciaTomo.tomo_id == tomo_id
        ).order_by(DiligenciaTomo.fecha).all()

        alertas = []
        for i in range(len(diligencias) - 1):
            dias_diff = (diligencias[i+1].fecha - diligencias[i].fecha).days
            if dias_diff > umbral_dias:
                alerta = AlertaInactividad(
                    tomo_id=tomo_id,
                    ultima_diligencia=diligencias[i].fecha,
                    dias_inactividad=dias_diff,
                    estado='activa'
                )
                self.db.add(alerta)
                alertas.append(alerta)

        return alertas

    def estadisticas_declaraciones(self, tomo_id: int) -> Dict:
        """Genera estadísticas sobre las declaraciones por persona"""
        return self.db.query(
            PersonaMencionada.nombre,
            func.count(Declaracion.id).label('total_declaraciones'),
            func.min(Declaracion.fecha).label('primera_declaracion'),
            func.max(Declaracion.fecha).label('ultima_declaracion')
        ).join(Declaracion).filter(
            PersonaMencionada.tomo_id == tomo_id
        ).group_by(PersonaMencionada.nombre).all()

    def _parsear_fecha(self, texto_fecha: str) -> Optional[datetime]:
        """Convierte texto de fecha a objeto datetime"""
        try:
            dia, mes, anio = map(int, texto_fecha.split('/'))
            return datetime(anio, mes, dia)
        except:
            return None