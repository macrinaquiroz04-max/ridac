# backend/app/controllers/busqueda_tomo_controller.py

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, text, func
from fastapi import HTTPException, status
from typing import List, Dict, Optional, Tuple
from datetime import datetime, date
import re

from app.models.tomo import Tomo, ContenidoOCR
from app.models.carpeta import Carpeta
from app.models.permiso_tomo import PermisoTomo
from app.controllers.permiso_tomo_controller import PermisoTomoController

class BusquedaTomoController:
    
    @staticmethod
    def buscar_en_tomo(db: Session, usuario_id: int, tomo_id: int, 
                      termino_busqueda: str, **filtros) -> Dict:
        """
        Busca un término específico dentro del contenido OCR de un tomo
        """
        # Verificar permisos de búsqueda
        if not PermisoTomoController.verificar_permiso(db, usuario_id, tomo_id, "buscar"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para buscar en este tomo"
            )
        
        # Obtener información del tomo
        tomo = db.query(Tomo).filter(Tomo.id == tomo_id).first()
        if not tomo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tomo no encontrado"
            )
        
        # Construir consulta de búsqueda
        query = db.query(ContenidoOCR).filter(
            ContenidoOCR.tomo_id == tomo_id
        )
        
        # Aplicar filtros adicionales
        if filtros.get("pagina_inicio"):
            query = query.filter(ContenidoOCR.numero_pagina >= filtros["pagina_inicio"])
        
        if filtros.get("pagina_fin"):
            query = query.filter(ContenidoOCR.numero_pagina <= filtros["pagina_fin"])
        
        if filtros.get("confianza_minima"):
            query = query.filter(ContenidoOCR.confianza >= filtros["confianza_minima"])
        
        # Búsqueda en texto extraído
        if termino_busqueda:
            # Búsqueda insensible a mayúsculas
            query = query.filter(
                func.lower(ContenidoOCR.texto_extraido).contains(func.lower(termino_busqueda))
            )
        
        # Ordenar por número de página
        resultados = query.order_by(ContenidoOCR.numero_pagina).all()
        
        # Procesar resultados con contexto
        coincidencias = []
        for contenido in resultados:
            if contenido.texto_extraido:
                contextos = BusquedaTomoController._extraer_contextos(
                    contenido.texto_extraido, termino_busqueda
                )
                
                for contexto in contextos:
                    coincidencias.append({
                        "pagina": contenido.numero_pagina,
                        "confianza": float(contenido.confianza) if contenido.confianza else 0,
                        "contexto": contexto["texto"],
                        "posicion_inicio": contexto["inicio"],
                        "posicion_fin": contexto["fin"],
                        "fecha_extraccion": contenido.created_at.isoformat()
                    })
        
        return {
            "tomo": {
                "id": tomo.id,
                "numero_tomo": tomo.numero_tomo,
                "nombre_archivo": tomo.nombre_archivo,
                "numero_paginas": tomo.numero_paginas
            },
            "termino_busqueda": termino_busqueda,
            "total_coincidencias": len(coincidencias),
            "coincidencias": coincidencias,
            "filtros_aplicados": filtros
        }
    
    @staticmethod
    def buscar_en_multiples_tomos(db: Session, usuario_id: int, termino_busqueda: str,
                                tomos_ids: Optional[List[int]] = None, **filtros) -> Dict:
        """
        Busca un término en múltiples tomos con permisos del usuario
        """
        # Obtener tomos accesibles por el usuario
        if tomos_ids:
            # Verificar permisos para tomos específicos
            tomos_permitidos = []
            for tomo_id in tomos_ids:
                if PermisoTomoController.verificar_permiso(db, usuario_id, tomo_id, "buscar"):
                    tomos_permitidos.append(tomo_id)
        else:
            # Obtener todos los tomos con permisos de búsqueda
            permisos_query = db.query(PermisoTomo).filter(
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_buscar == True
            )
            tomos_permitidos = [p.tomo_id for p in permisos_query.all()]
        
        if not tomos_permitidos:
            return {
                "termino_busqueda": termino_busqueda,
                "total_tomos_buscados": 0,
                "total_coincidencias": 0,
                "resultados_por_tomo": [],
                "mensaje": "No tienes permisos de búsqueda en ningún tomo"
            }
        
        resultados_por_tomo = []
        total_coincidencias = 0
        
        for tomo_id in tomos_permitidos:
            try:
                resultado_tomo = BusquedaTomoController.buscar_en_tomo(
                    db, usuario_id, tomo_id, termino_busqueda, **filtros
                )
                
                if resultado_tomo["total_coincidencias"] > 0:
                    resultados_por_tomo.append(resultado_tomo)
                    total_coincidencias += resultado_tomo["total_coincidencias"]
                    
            except HTTPException:
                # Ignorar tomos sin permisos o no encontrados
                continue
        
        # Ordenar por relevancia (número de coincidencias)
        resultados_por_tomo.sort(
            key=lambda x: x["total_coincidencias"], 
            reverse=True
        )
        
        return {
            "termino_busqueda": termino_busqueda,
            "total_tomos_buscados": len(tomos_permitidos),
            "total_tomos_con_coincidencias": len(resultados_por_tomo),
            "total_coincidencias": total_coincidencias,
            "resultados_por_tomo": resultados_por_tomo,
            "filtros_aplicados": filtros
        }
    
    @staticmethod
    def busqueda_cronologica(db: Session, usuario_id: int, termino_busqueda: str,
                           carpeta_id: Optional[int] = None, **filtros) -> Dict:
        """
        Realiza búsqueda cronológica por fecha de procesamiento de tomos
        """
        # Query base para obtener tomos con permisos
        query = db.query(Tomo, ContenidoOCR, Carpeta).join(
            ContenidoOCR, Tomo.id == ContenidoOCR.tomo_id
        ).join(
            Carpeta, Tomo.carpeta_id == Carpeta.id
        ).join(
            PermisoTomo, and_(
                PermisoTomo.tomo_id == Tomo.id,
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_buscar == True
            )
        )
        
        # Filtrar por carpeta si se especifica
        if carpeta_id:
            query = query.filter(Tomo.carpeta_id == carpeta_id)
        
        # Filtros de fecha
        if filtros.get("fecha_inicio"):
            query = query.filter(Tomo.fecha_procesamiento >= filtros["fecha_inicio"])
        
        if filtros.get("fecha_fin"):
            query = query.filter(Tomo.fecha_procesamiento <= filtros["fecha_fin"])
        
        # Búsqueda en contenido
        if termino_busqueda:
            query = query.filter(
                func.lower(ContenidoOCR.texto_extraido).contains(func.lower(termino_busqueda))
            )
        
        # Ejecutar consulta y agrupar por fecha
        resultados = query.order_by(
            Tomo.fecha_procesamiento.desc(),
            Tomo.numero_tomo.asc(),
            ContenidoOCR.numero_pagina.asc()
        ).all()
        
        # Agrupar resultados por fecha de procesamiento
        resultados_cronologicos = {}
        
        for tomo, contenido, carpeta in resultados:
            fecha_procesamiento = tomo.fecha_procesamiento.date() if tomo.fecha_procesamiento else None
            fecha_key = fecha_procesamiento.isoformat() if fecha_procesamiento else "sin_fecha"
            
            if fecha_key not in resultados_cronologicos:
                resultados_cronologicos[fecha_key] = {
                    "fecha": fecha_procesamiento.isoformat() if fecha_procesamiento else None,
                    "total_coincidencias": 0,
                    "tomos": {}
                }
            
            tomo_key = f"{carpeta.numero_expediente}-{tomo.numero_tomo}"
            if tomo_key not in resultados_cronologicos[fecha_key]["tomos"]:
                resultados_cronologicos[fecha_key]["tomos"][tomo_key] = {
                    "tomo_id": tomo.id,
                    "carpeta_nombre": carpeta.nombre,
                    "carpeta_codigo": carpeta.numero_expediente,
                    "numero_tomo": tomo.numero_tomo,
                    "nombre_archivo": tomo.nombre_archivo,
                    "coincidencias": []
                }
            
            # Extraer contextos de la coincidencia
            if contenido.texto_extraido:
                contextos = BusquedaTomoController._extraer_contextos(
                    contenido.texto_extraido, termino_busqueda
                )
                
                for contexto in contextos:
                    resultados_cronologicos[fecha_key]["tomos"][tomo_key]["coincidencias"].append({
                        "pagina": contenido.numero_pagina,
                        "confianza": float(contenido.confianza) if contenido.confianza else 0,
                        "contexto": contexto["texto"],
                        "posicion_inicio": contexto["inicio"],
                        "posicion_fin": contexto["fin"]
                    })
                    
                    resultados_cronologicos[fecha_key]["total_coincidencias"] += 1
        
        # Convertir a lista ordenada
        timeline = []
        for fecha_key in sorted(resultados_cronologicos.keys(), reverse=True):
            entrada = resultados_cronologicos[fecha_key]
            entrada["tomos"] = list(entrada["tomos"].values())
            timeline.append(entrada)
        
        return {
            "termino_busqueda": termino_busqueda,
            "tipo_busqueda": "cronologica",
            "total_fechas": len(timeline),
            "total_coincidencias": sum(entrada["total_coincidencias"] for entrada in timeline),
            "timeline": timeline,
            "filtros_aplicados": filtros
        }
    
    @staticmethod
    def busqueda_avanzada(db: Session, usuario_id: int, parametros: Dict) -> Dict:
        """
        Búsqueda avanzada con múltiples criterios y operadores
        """
        terminos = parametros.get("terminos", [])  # Lista de términos
        operador = parametros.get("operador", "AND")  # AND, OR
        frase_exacta = parametros.get("frase_exacta", "")
        excluir_terminos = parametros.get("excluir_terminos", [])
        
        # Query base
        query = db.query(ContenidoOCR, Tomo, Carpeta).join(
            Tomo, ContenidoOCR.tomo_id == Tomo.id
        ).join(
            Carpeta, Tomo.carpeta_id == Carpeta.id
        ).join(
            PermisoTomo, and_(
                PermisoTomo.tomo_id == Tomo.id,
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_buscar == True
            )
        )
        
        # Construir condiciones de búsqueda
        condiciones = []
        
        # Búsqueda de términos individuales
        if terminos:
            if operador.upper() == "AND":
                for termino in terminos:
                    condiciones.append(
                        func.lower(ContenidoOCR.texto_extraido).contains(func.lower(termino))
                    )
            else:  # OR
                condiciones_or = [
                    func.lower(ContenidoOCR.texto_extraido).contains(func.lower(termino))
                    for termino in terminos
                ]
                if condiciones_or:
                    condiciones.append(or_(*condiciones_or))
        
        # Frase exacta
        if frase_exacta:
            condiciones.append(
                func.lower(ContenidoOCR.texto_extraido).contains(func.lower(frase_exacta))
            )
        
        # Excluir términos
        for termino_excluir in excluir_terminos:
            condiciones.append(
                ~func.lower(ContenidoOCR.texto_extraido).contains(func.lower(termino_excluir))
            )
        
        # Aplicar condiciones
        if condiciones:
            query = query.filter(and_(*condiciones))
        
        # Aplicar filtros adicionales
        filtros = parametros.get("filtros", {})
        
        if filtros.get("carpeta_id"):
            query = query.filter(Tomo.carpeta_id == filtros["carpeta_id"])
        
        if filtros.get("fecha_inicio"):
            query = query.filter(Tomo.fecha_procesamiento >= filtros["fecha_inicio"])
        
        if filtros.get("fecha_fin"):
            query = query.filter(Tomo.fecha_procesamiento <= filtros["fecha_fin"])
        
        if filtros.get("confianza_minima"):
            query = query.filter(ContenidoOCR.confianza >= filtros["confianza_minima"])
        
        # Ejecutar y procesar resultados
        resultados = query.order_by(
            Carpeta.numero_expediente.asc(),
            Tomo.numero_tomo.asc(),
            ContenidoOCR.numero_pagina.asc()
        ).all()
        
        coincidencias = []
        for contenido, tomo, carpeta in resultados:
            if contenido.texto_extraido:
                # Crear término compuesto para extraer contextos
                termino_busqueda = " ".join(terminos) if terminos else frase_exacta
                
                contextos = BusquedaTomoController._extraer_contextos(
                    contenido.texto_extraido, termino_busqueda
                )
                
                for contexto in contextos:
                    coincidencias.append({
                        "tomo_id": tomo.id,
                        "carpeta_nombre": carpeta.nombre,
                        "carpeta_codigo": carpeta.numero_expediente,
                        "numero_tomo": tomo.numero_tomo,
                        "nombre_archivo": tomo.nombre_archivo,
                        "pagina": contenido.numero_pagina,
                        "confianza": float(contenido.confianza) if contenido.confianza else 0,
                        "contexto": contexto["texto"],
                        "fecha_procesamiento": tomo.fecha_procesamiento.isoformat() if tomo.fecha_procesamiento else None
                    })
        
        return {
            "tipo_busqueda": "avanzada",
            "parametros": parametros,
            "total_coincidencias": len(coincidencias),
            "coincidencias": coincidencias
        }
    
    @staticmethod
    def _extraer_contextos(texto: str, termino: str, contexto_chars: int = 150) -> List[Dict]:
        """
        Extrae contextos alrededor de las coincidencias del término en el texto
        """
        if not texto or not termino:
            return []
        
        contextos = []
        texto_lower = texto.lower()
        termino_lower = termino.lower()
        
        # Encontrar todas las posiciones del término
        start = 0
        while True:
            pos = texto_lower.find(termino_lower, start)
            if pos == -1:
                break
            
            # Calcular inicio y fin del contexto
            inicio_contexto = max(0, pos - contexto_chars)
            fin_contexto = min(len(texto), pos + len(termino) + contexto_chars)
            
            # Ajustar para no cortar palabras
            if inicio_contexto > 0:
                # Buscar el inicio de palabra más cercano
                while inicio_contexto > 0 and texto[inicio_contexto] not in ' \n\t':
                    inicio_contexto -= 1
            
            if fin_contexto < len(texto):
                # Buscar el fin de palabra más cercano
                while fin_contexto < len(texto) and texto[fin_contexto] not in ' \n\t':
                    fin_contexto += 1
            
            contexto_texto = texto[inicio_contexto:fin_contexto].strip()
            
            # Agregar indicadores si el contexto está truncado
            if inicio_contexto > 0:
                contexto_texto = "..." + contexto_texto
            if fin_contexto < len(texto):
                contexto_texto = contexto_texto + "..."
            
            contextos.append({
                "texto": contexto_texto,
                "inicio": pos,
                "fin": pos + len(termino),
                "posicion_relativa": inicio_contexto
            })
            
            start = pos + 1
        
        return contextos
    
    @staticmethod
    def obtener_estadisticas_busqueda(db: Session, usuario_id: int) -> Dict:
        """
        Obtiene estadísticas de búsqueda disponibles para el usuario
        """
        # Contar tomos con permisos de búsqueda
        tomos_query = db.query(Tomo).join(
            PermisoTomo, and_(
                PermisoTomo.tomo_id == Tomo.id,
                PermisoTomo.usuario_id == usuario_id,
                PermisoTomo.puede_buscar == True
            )
        )
        
        tomos_con_permisos = tomos_query.all()
        
        # Estadísticas por carpeta
        estadisticas_carpetas = {}
        total_paginas = 0
        
        for tomo in tomos_con_permisos:
            carpeta_id = tomo.carpeta_id
            if carpeta_id not in estadisticas_carpetas:
                carpeta = db.query(Carpeta).filter(Carpeta.id == carpeta_id).first()
                estadisticas_carpetas[carpeta_id] = {
                    "carpeta_nombre": carpeta.nombre if carpeta else "Desconocida",
                    "carpeta_codigo": carpeta.numero_expediente if carpeta else "",
                    "total_tomos": 0,
                    "total_paginas": 0
                }
            
            estadisticas_carpetas[carpeta_id]["total_tomos"] += 1
            estadisticas_carpetas[carpeta_id]["total_paginas"] += tomo.numero_paginas or 0
            total_paginas += tomo.numero_paginas or 0
        
        return {
            "total_tomos_con_acceso": len(tomos_con_permisos),
            "total_paginas_disponibles": total_paginas,
            "total_carpetas": len(estadisticas_carpetas),
            "estadisticas_por_carpeta": list(estadisticas_carpetas.values()),
            "fecha_consulta": datetime.utcnow().isoformat()
        }