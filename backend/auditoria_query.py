#!/usr/bin/env python3
"""
Sistema de Auditoría Avanzado para Sistema OCR RIDAC
Permite consultar logs de auditoría de forma detallada
"""

import sys
import os
sys.path.append('/app')

from app.database import SessionLocal
from app.models.auditoria import Auditoria
from app.models.usuario import Usuario
from datetime import datetime, timedelta
import json

def get_auditoria_por_usuario(username=None, dias=7):
    """Obtener auditoría por usuario"""
    db = SessionLocal()
    try:
        query = db.query(Auditoria, Usuario).outerjoin(Usuario, Auditoria.usuario_id == Usuario.id)
        
        # Filtrar por fecha (últimos N días)
        fecha_inicio = datetime.now() - timedelta(days=dias)
        query = query.filter(Auditoria.created_at >= fecha_inicio)
        
        # Filtrar por usuario si se especifica
        if username:
            query = query.filter(Usuario.username == username)
        
        # Ordenar por fecha descendente
        results = query.order_by(Auditoria.created_at.desc()).all()
        
        print(f"\n🔍 AUDITORÍA - Últimos {dias} días")
        if username:
            print(f"👤 Usuario: {username}")
        print("=" * 80)
        
        for auditoria, usuario in results:
            user_info = usuario.username if usuario else "Sistema/Usuario eliminado"
            
            print(f"\n📅 {auditoria.created_at}")
            print(f"👤 Usuario: {user_info}")
            print(f"🎯 Acción: {auditoria.accion}")
            print(f"📋 Tabla: {auditoria.tabla_afectada}")
            
            if auditoria.registro_id:
                print(f"🆔 ID Registro: {auditoria.registro_id}")
            
            if auditoria.ip_address:
                print(f"🌐 IP: {auditoria.ip_address}")
            
            if auditoria.valores_anteriores:
                print(f"📝 Valores Anteriores:")
                for key, value in auditoria.valores_anteriores.items():
                    if key not in ['password', 'password_hash']:  # No mostrar contraseñas
                        print(f"   • {key}: {value}")
            
            if auditoria.valores_nuevos:
                print(f"✨ Valores Nuevos:")
                for key, value in auditoria.valores_nuevos.items():
                    if key not in ['password', 'password_hash']:  # No mostrar contraseñas
                        print(f"   • {key}: {value}")
            
            print("-" * 60)
        
        total = len(results)
        print(f"\n📊 Total de eventos: {total}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def get_estadisticas_auditoria(dias=7):
    """Obtener estadísticas de auditoría"""
    db = SessionLocal()
    try:
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        # Total de eventos
        total = db.query(Auditoria).filter(Auditoria.created_at >= fecha_inicio).count()
        
        # Eventos por acción
        acciones = db.query(Auditoria.accion, db.func.count(Auditoria.id)).filter(
            Auditoria.created_at >= fecha_inicio
        ).group_by(Auditoria.accion).all()
        
        # Eventos por usuario
        usuarios = db.query(Usuario.username, db.func.count(Auditoria.id)).outerjoin(
            Auditoria, Usuario.id == Auditoria.usuario_id
        ).filter(Auditoria.created_at >= fecha_inicio).group_by(Usuario.username).all()
        
        # Eventos por tabla
        tablas = db.query(Auditoria.tabla_afectada, db.func.count(Auditoria.id)).filter(
            Auditoria.created_at >= fecha_inicio
        ).group_by(Auditoria.tabla_afectada).all()
        
        print(f"\n📊 ESTADÍSTICAS DE AUDITORÍA - Últimos {dias} días")
        print("=" * 60)
        print(f"📈 Total de eventos: {total}")
        
        print(f"\n🎯 Eventos por Acción:")
        for accion, count in sorted(acciones, key=lambda x: x[1], reverse=True):
            print(f"   • {accion}: {count}")
        
        print(f"\n👥 Eventos por Usuario:")
        for username, count in sorted(usuarios, key=lambda x: x[1], reverse=True):
            print(f"   • {username}: {count}")
        
        print(f"\n📋 Eventos por Tabla:")
        for tabla, count in sorted(tablas, key=lambda x: x[1], reverse=True):
            print(f"   • {tabla}: {count}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def get_eventos_criticos(dias=7):
    """Obtener eventos críticos de auditoría"""
    db = SessionLocal()
    try:
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        # Acciones críticas a monitorear
        acciones_criticas = [
            'ELIMINAR_USUARIO',
            'CREAR_USUARIO',
            'MODIFICAR_PERMISOS',
            'ELIMINAR_CARPETA',
            'CAMBIAR_PASSWORD',
            'LOGIN_FALLIDO',
            'CONFIGURAR_SISTEMA'
        ]
        
        query = db.query(Auditoria, Usuario).outerjoin(Usuario, Auditoria.usuario_id == Usuario.id)
        query = query.filter(
            Auditoria.created_at >= fecha_inicio,
            Auditoria.accion.in_(acciones_criticas)
        )
        
        results = query.order_by(Auditoria.created_at.desc()).all()
        
        print(f"\n🚨 EVENTOS CRÍTICOS - Últimos {dias} días")
        print("=" * 60)
        
        for auditoria, usuario in results:
            user_info = usuario.username if usuario else "Sistema/Usuario eliminado"
            
            print(f"\n⚠️  {auditoria.created_at}")
            print(f"👤 Usuario: {user_info}")
            print(f"🚨 Acción Crítica: {auditoria.accion}")
            print(f"📋 Tabla: {auditoria.tabla_afectada}")
            
            if auditoria.ip_address:
                print(f"🌐 IP: {auditoria.ip_address}")
            
            print("-" * 40)
        
        print(f"\n📊 Total de eventos críticos: {len(results)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def buscar_por_ip(ip_address, dias=30):
    """Buscar eventos por dirección IP"""
    db = SessionLocal()
    try:
        fecha_inicio = datetime.now() - timedelta(days=dias)
        
        query = db.query(Auditoria, Usuario).outerjoin(Usuario, Auditoria.usuario_id == Usuario.id)
        query = query.filter(
            Auditoria.created_at >= fecha_inicio,
            Auditoria.ip_address == ip_address
        )
        
        results = query.order_by(Auditoria.created_at.desc()).all()
        
        print(f"\n🔍 EVENTOS DESDE IP: {ip_address}")
        print("=" * 60)
        
        for auditoria, usuario in results:
            user_info = usuario.username if usuario else "Sistema/Usuario eliminado"
            
            print(f"\n📅 {auditoria.created_at}")
            print(f"👤 Usuario: {user_info}")
            print(f"🎯 Acción: {auditoria.accion}")
            print(f"📋 Tabla: {auditoria.tabla_afectada}")
            print("-" * 40)
        
        print(f"\n📊 Total de eventos desde esta IP: {len(results)}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

def main():
    """Función principal para consulta de auditoría"""
    if len(sys.argv) < 2:
        print("""
🔍 Sistema de Consulta de Auditoría - OCR RIDAC

Uso: python auditoria_query.py <comando> [opciones]

Comandos disponibles:
  usuario <username> [dias]    - Ver auditoría de un usuario específico
  estadisticas [dias]          - Ver estadísticas generales
  criticos [dias]              - Ver eventos críticos
  ip <direccion_ip> [dias]     - Ver eventos desde una IP
  todos [dias]                 - Ver todos los eventos recientes

Ejemplos:
  python auditoria_query.py usuario eduardo 7
  python auditoria_query.py estadisticas 30
  python auditoria_query.py criticos 7
  python auditoria_query.py ip 192.168.1.100 30
  python auditoria_query.py todos 3
        """)
        return
    
    comando = sys.argv[1]
    
    try:
        if comando == "usuario":
            username = sys.argv[2] if len(sys.argv) > 2 else None
            dias = int(sys.argv[3]) if len(sys.argv) > 3 else 7
            get_auditoria_por_usuario(username, dias)
        
        elif comando == "estadisticas":
            dias = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            get_estadisticas_auditoria(dias)
        
        elif comando == "criticos":
            dias = int(sys.argv[2]) if len(sys.argv) > 2 else 7
            get_eventos_criticos(dias)
        
        elif comando == "ip":
            ip_address = sys.argv[2] if len(sys.argv) > 2 else None
            dias = int(sys.argv[3]) if len(sys.argv) > 3 else 30
            if ip_address:
                buscar_por_ip(ip_address, dias)
            else:
                print("❌ Debe especificar una dirección IP")
        
        elif comando == "todos":
            dias = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            get_auditoria_por_usuario(None, dias)
        
        else:
            print(f"❌ Comando desconocido: {comando}")
    
    except ValueError:
        print("❌ Error: El número de días debe ser un entero")
    except IndexError:
        print("❌ Error: Parámetros insuficientes")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    main()