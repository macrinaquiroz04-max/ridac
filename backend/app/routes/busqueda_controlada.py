from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.services.busqueda_controlada_service import BusquedaControladaService
from app.middlewares.auth_middleware import get_current_user
from app.models.usuario import Usuario

router = APIRouter()

class BusquedaRequest(BaseModel):
    texto_busqueda: str
    tomo_id: Optional[int] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    pagina_inicio: Optional[int] = None
    pagina_fin: Optional[int] = None

class ResultadoBusquedaResponse(BaseModel):
    tomo_id: int
    pagina: int
    texto_encontrado: str
    contexto: str
    fecha: Optional[datetime] = None

class BusquedaResponse(BaseModel):
    resultados: List[ResultadoBusquedaResponse]
    total_resultados: int
    tomos_analizados: int

@router.post("/busqueda-controlada/", response_model=BusquedaResponse)
async def buscar_en_tomos(
    busqueda: BusquedaRequest,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Realiza una búsqueda controlada en los tomos a los que el usuario tiene acceso.
    No permite la descarga completa del contenido, solo muestra fragmentos relevantes.
    """
    service = BusquedaControladaService(db)
    
    try:
        if busqueda.tomo_id:
            # Búsqueda en un tomo específico
            resultados_raw = service.buscar_en_tomo(
                current_user.id,
                busqueda.tomo_id,
                busqueda.texto_busqueda,
                busqueda.fecha_inicio,
                busqueda.fecha_fin,
                busqueda.pagina_inicio,
                busqueda.pagina_fin
            )
            resultados_dict = {busqueda.tomo_id: resultados_raw}
            tomos_analizados = 1
        else:
            # Búsqueda en todos los tomos permitidos
            resultados_dict = service.buscar_en_tomos_permitidos(
                current_user.id,
                busqueda.texto_busqueda,
                busqueda.fecha_inicio,
                busqueda.fecha_fin
            )
            tomos_analizados = len(resultados_dict)

        # Convertir resultados al formato de respuesta
        resultados_format = []
        for tomo_id, resultados in resultados_dict.items():
            for res in resultados:
                resultados_format.append(
                    ResultadoBusquedaResponse(
                        tomo_id=res.tomo_id,
                        pagina=res.pagina,
                        texto_encontrado=res.texto,
                        contexto=res.contexto,
                        fecha=res.fecha
                    )
                )

        return BusquedaResponse(
            resultados=resultados_format,
            total_resultados=len(resultados_format),
            tomos_analizados=tomos_analizados
        )

    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al realizar la búsqueda: {str(e)}")

@router.get("/busqueda-controlada/tomos-permitidos/")
async def listar_tomos_permitidos(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retorna la lista de tomos en los que el usuario puede realizar búsquedas
    """
    service = BusquedaControladaService(db)
    permisos = db.query(PermisoTomo).filter(
        PermisoTomo.usuario_id == current_user.id,
        PermisoTomo.puede_buscar == True
    ).all()
    
    return [{
        "tomo_id": p.tomo_id,
        "puede_ver_sellos": p.puede_ver_sellos,
        "puede_extraer_texto": p.puede_extraer_texto,
        "busqueda_cronologica": p.busqueda_cronologica,
        "fecha_inicio_acceso": p.fecha_inicio_acceso,
        "fecha_fin_acceso": p.fecha_fin_acceso
    } for p in permisos]