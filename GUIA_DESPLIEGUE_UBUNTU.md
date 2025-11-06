# 🚀 Guía de Despliegue en Servidor Ubuntu

## Sistema OCR FGJCDMX - Despliegue en Producción
**Desarrollador:** Eduardo Lozada Quiroz, ISC  
**Fecha:** Noviembre 2025

---

## 📋 Pre-requisitos en el Servidor Ubuntu

### 1. Características del Servidor Recomendadas
```
- Ubuntu 20.04 LTS o superior
- RAM: Mínimo 8GB (Recomendado 16GB)
- CPU: Mínimo 4 cores (Recomendado 8 cores)
- Disco: Mínimo 100GB SSD
- Acceso root o sudo
```

### 2. Software Necesario

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose -y

# Instalar herramientas adicionales
sudo apt install -y git curl wget htop net-tools
```

---

## 📦 Método 1: Despliegue con Docker (RECOMENDADO)

### Paso 1: Transferir Proyecto al Servidor

**Opción A - Desde repositorio Git:**
```bash
cd /opt
sudo git clone <tu-repositorio> sistemaocr
sudo chown -R $USER:$USER /opt/sistemaocr
```

**Opción B - Transferir por SCP:**
```bash
# Desde tu máquina local
tar -czf sistemaocr.tar.gz /home/eduardolozada/Downloads/sistemaocr
scp sistemaocr.tar.gz usuario@servidor:/opt/

# En el servidor
cd /opt
tar -xzf sistemaocr.tar.gz
mv sistemaocr sistemaocr
```

**Opción C - Usar rsync (Mejor opción):**
```bash
# Desde tu máquina local
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '*.pyc' \
  --exclude '__pycache__' \
  /home/eduardolozada/Downloads/sistemaocr/ \
  usuario@IP_SERVIDOR:/opt/sistemaocr/
```

### Paso 2: Configurar Variables de Entorno

```bash
cd /opt/sistemaocr

# Crear archivo .env para producción
cat > .env.prod << 'EOF'
# Base de Datos
DB_HOST=postgres
DB_PORT=5432
DB_NAME=sistema_ocr
DB_USER=postgres
DB_PASSWORD=TU_PASSWORD_SEGURO_AQUI

# JWT Secret (genera uno único)
JWT_SECRET_KEY=CAMBIA_ESTO_POR_ALGO_MUY_SEGURO_Y_LARGO

# Configuración del servidor
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
TZ=America/Mexico_City

# Configuración de producción
ENVIRONMENT=production
DEBUG=False
EOF

chmod 600 .env.prod
```

### Paso 3: Configurar IP del Servidor

```bash
# Editar configuración de red
sudo nano /opt/sistemaocr/config/01-netcfg.yaml

# Cambiar la IP a la IP de tu servidor
# Ejemplo: 192.168.1.100 o la IP pública
```

### Paso 4: Construir Imágenes Docker

```bash
cd /opt/sistemaocr

# Construir imágenes
docker compose -f docker-compose.prod.yml build --no-cache

# Verificar imágenes creadas
docker images | grep sistemaocr
```

### Paso 5: Iniciar Servicios

```bash
# Iniciar servicios en producción
docker compose -f docker-compose.prod.yml up -d

# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f

# Verificar estado
docker compose -f docker-compose.prod.yml ps
```

### Paso 6: Restaurar Base de Datos

```bash
# Copiar backup al servidor (si tienes uno)
scp backups/sistema_ocr_backup_*.sql.gz usuario@servidor:/opt/sistemaocr/backups/

# En el servidor, restaurar backup
cd /opt/sistemaocr
gunzip -c backups/sistema_ocr_backup_*.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d sistema_ocr

# Crear función para IDs secuenciales
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d sistema_ocr < backend/scripts/reutilizar_ids.sql
```

### Paso 7: Configurar Firewall

```bash
# Instalar UFW si no está instalado
sudo apt install ufw -y

# Configurar reglas
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8000/tcp  # API (si es necesario)

# Activar firewall
sudo ufw enable
sudo ufw status
```

### Paso 8: Configurar NGINX como Reverse Proxy (Opcional)

```bash
# Instalar NGINX
sudo apt install nginx -y

# Crear configuración
sudo nano /etc/nginx/sites-available/sistema-ocr

# Pegar esta configuración:
```

```nginx
server {
    listen 80;
    server_name tu-dominio.com;  # o IP del servidor
    
    client_max_body_size 500M;
    
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

```bash
# Activar configuración
sudo ln -s /etc/nginx/sites-available/sistema-ocr /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Paso 9: Configurar SSL con Let's Encrypt (Opcional pero Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado SSL
sudo certbot --nginx -d tu-dominio.com

# Renovación automática ya está configurada
```

---

## 🔄 Scripts de Automatización

### Script de Inicio Automático

```bash
# Crear servicio systemd
sudo nano /etc/systemd/system/sistema-ocr.service
```

```ini
[Unit]
Description=Sistema OCR FGJCDMX
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/sistemaocr
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
User=root

[Install]
WantedBy=multi-user.target
```

```bash
# Activar servicio
sudo systemctl daemon-reload
sudo systemctl enable sistema-ocr.service
sudo systemctl start sistema-ocr.service

# Verificar estado
sudo systemctl status sistema-ocr.service
```

### Script de Backup Automático

```bash
# Crear script de backup
sudo nano /opt/sistemaocr/backup-auto.sh
```

```bash
#!/bin/bash
cd /opt/sistemaocr
./backup-database.sh
# Eliminar backups antiguos (mantener últimos 7 días)
find backups/ -name "*.sql.gz" -mtime +7 -delete
```

```bash
# Dar permisos
chmod +x /opt/sistemaocr/backup-auto.sh

# Configurar cron (backup diario a las 2 AM)
crontab -e
# Agregar línea:
0 2 * * * /opt/sistemaocr/backup-auto.sh >> /var/log/sistema-ocr-backup.log 2>&1
```

---

## 🔍 Monitoreo y Mantenimiento

### Verificar Estado del Sistema

```bash
# Ver logs de todos los servicios
docker compose -f docker-compose.prod.yml logs -f

# Ver logs de un servicio específico
docker compose -f docker-compose.prod.yml logs -f backend

# Ver uso de recursos
docker stats

# Ver estado de salud
curl http://localhost/health
```

### Comandos Útiles

```bash
# Reiniciar todo el sistema
docker compose -f docker-compose.prod.yml restart

# Reiniciar solo backend
docker compose -f docker-compose.prod.yml restart backend

# Ver base de datos
docker compose -f docker-compose.prod.yml exec postgres psql -U postgres -d sistema_ocr

# Actualizar sistema
cd /opt/sistemaocr
git pull  # o rsync desde tu máquina
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

---

## 🛡️ Seguridad Adicional

### 1. Cambiar Contraseñas por Defecto
```bash
# En la base de datos, cambiar password del usuario eduardo
docker compose -f docker-compose.prod.yml exec backend \
  python reset_password.py eduardo NUEVA_PASSWORD_SEGURA
```

### 2. Configurar Fail2Ban
```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### 3. Limitar Acceso SSH
```bash
sudo nano /etc/ssh/sshd_config
# Cambiar:
# PermitRootLogin no
# PasswordAuthentication no (usar solo llaves)
sudo systemctl restart sshd
```

---

## 📊 URLs de Acceso en Producción

```
Frontend:        http://IP_SERVIDOR/
API Docs:        http://IP_SERVIDOR/docs
Health Check:    http://IP_SERVIDOR/health
PgAdmin:         http://IP_SERVIDOR:5050
```

---

## ⚠️ Troubleshooting

### Problema: Servicios no inician
```bash
# Ver logs detallados
docker compose -f docker-compose.prod.yml logs

# Verificar permisos
sudo chown -R $USER:$USER /opt/sistemaocr

# Verificar puertos
sudo netstat -tulpn | grep -E '80|443|5432|8000'
```

### Problema: Base de datos no conecta
```bash
# Verificar que postgres esté corriendo
docker compose -f docker-compose.prod.yml ps postgres

# Ver logs de postgres
docker compose -f docker-compose.prod.yml logs postgres

# Probar conexión
docker compose -f docker-compose.prod.yml exec postgres pg_isready
```

### Problema: Sin espacio en disco
```bash
# Limpiar imágenes Docker no usadas
docker system prune -a -f

# Limpiar logs antiguos
sudo find /var/lib/docker/containers -name "*.log" -delete
```

---

## 📝 Checklist de Despliegue

- [ ] Servidor Ubuntu con recursos adecuados
- [ ] Docker y Docker Compose instalados
- [ ] Proyecto transferido al servidor
- [ ] Variables de entorno configuradas (.env.prod)
- [ ] IP del servidor configurada
- [ ] Imágenes Docker construidas
- [ ] Servicios iniciados correctamente
- [ ] Base de datos restaurada
- [ ] Función de IDs secuenciales creada
- [ ] Firewall configurado
- [ ] NGINX configurado (opcional)
- [ ] SSL configurado (opcional)
- [ ] Servicio systemd configurado
- [ ] Backups automáticos configurados
- [ ] Contraseñas cambiadas
- [ ] Monitoreo configurado
- [ ] Documentación actualizada

---

## 🎯 Recomendación Final

**Para tu caso específico, te recomiendo:**

1. ✅ **Usar Docker Compose** con el archivo `docker-compose.prod.yml`
2. ✅ **Configurar NGINX** como reverse proxy
3. ✅ **Implementar SSL** con Let's Encrypt
4. ✅ **Configurar backups automáticos** diarios
5. ✅ **Usar systemd** para inicio automático
6. ✅ **Monitorear logs** regularmente

Esta es la forma más **robusta, segura y fácil de mantener** para producción.

---

**Contacto:** aduardolozada1958@gmail.com  
**Documentación completa:** Ver otros archivos GUIA_*.md en el proyecto
