# app/services/minio_service.py
# Sistema OCR con Análisis Jurídico
# Desarrollador: Eduardo Lozada Quiroz, ISC
# Organización: Unidad de Análisis y Contexto (UAyC)
# Año: 2025 - Propiedad Intelectual Registrada
# Firma Digital: ELQ-ISC-UAYC-10112025

import os
import io
from typing import Optional, BinaryIO
from app.utils.logger import logger

try:
    from minio import Minio
    from minio.error import S3Error
    _MINIO_AVAILABLE = True
except ImportError:
    _MINIO_AVAILABLE = False
    logger.warning("⚠️ Paquete 'minio' no instalado — almacenamiento MinIO deshabilitado")

class MinIOService:
    """Servicio de almacenamiento de objetos con MinIO"""
    
    def __init__(self):
        self.minio_client: Optional[Minio] = None
        self.enabled = False
        self.bucket_pdfs = "tomos-pdfs"
        self.bucket_thumbnails = "tomos-thumbnails"
        self._initialize()
    
    def _initialize(self):
        """Inicializar conexión con MinIO"""
        if not _MINIO_AVAILABLE:
            self.enabled = False
            return
        try:
            endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
            access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
            
            self.minio_client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False  # Cambiar a True en producción con HTTPS
            )
            
            # Verificar conexión
            self.minio_client.list_buckets()
            logger.info("✅ MinIO conectado exitosamente")
            self.enabled = True
            
            # Crear buckets si no existen
            self._crear_buckets()
            
        except Exception as e:
            logger.error(f"❌ Error conectando a MinIO: {e}")
            logger.warning("⚠️ Sistema funcionará con almacenamiento en PostgreSQL")
            self.enabled = False
    
    def _crear_buckets(self):
        """Crear buckets necesarios"""
        if not self.enabled:
            return
        
        try:
            buckets = [self.bucket_pdfs, self.bucket_thumbnails]
            
            for bucket in buckets:
                if not self.minio_client.bucket_exists(bucket):
                    self.minio_client.make_bucket(bucket)
                    logger.info(f"📦 Bucket '{bucket}' creado")
                else:
                    logger.debug(f"📦 Bucket '{bucket}' ya existe")
                    
        except Exception as e:
            logger.error(f"❌ Error creando buckets: {e}")
    
    def subir_pdf(self, tomo_id: int, pdf_data: bytes, filename: str) -> bool:
        """
        Subir PDF a MinIO
        
        Args:
            tomo_id: ID del tomo
            pdf_data: Datos binarios del PDF
            filename: Nombre del archivo
            
        Returns:
            True si se subió correctamente
        """
        if not self.enabled:
            return False
        
        try:
            object_name = f"tomo_{tomo_id}/{filename}"
            pdf_stream = io.BytesIO(pdf_data)
            
            self.minio_client.put_object(
                self.bucket_pdfs,
                object_name,
                pdf_stream,
                length=len(pdf_data),
                content_type='application/pdf'
            )
            
            logger.info(f"📤 PDF subido: {object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"❌ Error subiendo PDF: {e}")
            return False
    
    def obtener_pdf(self, tomo_id: int, filename: str) -> Optional[bytes]:
        """
        Obtener PDF desde MinIO
        
        Args:
            tomo_id: ID del tomo
            filename: Nombre del archivo
            
        Returns:
            Datos binarios del PDF o None
        """
        if not self.enabled:
            return None
        
        try:
            object_name = f"tomo_{tomo_id}/{filename}"
            response = self.minio_client.get_object(self.bucket_pdfs, object_name)
            pdf_data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"📥 PDF obtenido: {object_name}")
            return pdf_data
            
        except S3Error as e:
            logger.error(f"❌ Error obteniendo PDF: {e}")
            return None
    
    def eliminar_pdf(self, tomo_id: int, filename: str) -> bool:
        """
        Eliminar PDF de MinIO
        
        Args:
            tomo_id: ID del tomo
            filename: Nombre del archivo
            
        Returns:
            True si se eliminó correctamente
        """
        if not self.enabled:
            return False
        
        try:
            object_name = f"tomo_{tomo_id}/{filename}"
            self.minio_client.remove_object(self.bucket_pdfs, object_name)
            
            logger.info(f"🗑️ PDF eliminado: {object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"❌ Error eliminando PDF: {e}")
            return False
    
    def subir_thumbnail(self, tomo_id: int, imagen_data: bytes, page_num: int) -> bool:
        """
        Subir miniatura (thumbnail) de una página
        
        Args:
            tomo_id: ID del tomo
            imagen_data: Datos binarios de la imagen
            page_num: Número de página
            
        Returns:
            True si se subió correctamente
        """
        if not self.enabled:
            return False
        
        try:
            object_name = f"tomo_{tomo_id}/page_{page_num}.jpg"
            img_stream = io.BytesIO(imagen_data)
            
            self.minio_client.put_object(
                self.bucket_thumbnails,
                object_name,
                img_stream,
                length=len(imagen_data),
                content_type='image/jpeg'
            )
            
            logger.debug(f"📸 Thumbnail subida: {object_name}")
            return True
            
        except S3Error as e:
            logger.error(f"❌ Error subiendo thumbnail: {e}")
            return False
    
    def obtener_url_temporal(self, tomo_id: int, filename: str, expiry_seconds: int = 3600) -> Optional[str]:
        """
        Generar URL temporal para descargar PDF
        
        Args:
            tomo_id: ID del tomo
            filename: Nombre del archivo
            expiry_seconds: Tiempo de expiración en segundos (default: 1 hora)
            
        Returns:
            URL temporal o None
        """
        if not self.enabled:
            return None
        
        try:
            object_name = f"tomo_{tomo_id}/{filename}"
            url = self.minio_client.presigned_get_object(
                self.bucket_pdfs,
                object_name,
                expires=expiry_seconds
            )
            
            logger.info(f"🔗 URL temporal generada para: {object_name}")
            return url
            
        except S3Error as e:
            logger.error(f"❌ Error generando URL: {e}")
            return None
    
    def listar_archivos_tomo(self, tomo_id: int) -> list:
        """Listar todos los archivos de un tomo"""
        if not self.enabled:
            return []
        
        try:
            prefix = f"tomo_{tomo_id}/"
            objects = self.minio_client.list_objects(self.bucket_pdfs, prefix=prefix)
            
            archivos = [obj.object_name for obj in objects]
            return archivos
            
        except S3Error as e:
            logger.error(f"❌ Error listando archivos: {e}")
            return []

# Instancia global
minio_service = MinIOService()
