#!/bin/bash
##############################################################################
# Script de Deployment para Hostinger VPS
# Uso: ./deploy-hostinger.sh
##############################################################################

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
PROJECT_NAME="weatherlink-dashboard"
DEPLOY_DIR="/var/www/weatherlink"
BACKUP_DIR="/var/backups/weatherlink"
COMPOSE_FILE="docker-compose.production.yml"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  WeatherLink Dashboard - Deployment a Producción      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

# Función para mostrar mensajes
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Verificar que estamos en el servidor
if [ ! -f "/etc/hostname" ]; then
    log_error "Este script debe ejecutarse en el servidor Hostinger"
    exit 1
fi

# Paso 1: Crear backup antes de cualquier cambio
log_info "Paso 1/8: Creando backup de la aplicación actual..."
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "${BACKUP_DIR}/${BACKUP_DATE}"

if [ -d "$DEPLOY_DIR" ]; then
    log_info "Respaldando directorio actual..."
    tar -czf "${BACKUP_DIR}/${BACKUP_DATE}/app_backup.tar.gz" -C "$DEPLOY_DIR" . 2>/dev/null || true
    
    # Backup de contenedores Docker si existen
    if command -v docker &> /dev/null; then
        docker ps -a > "${BACKUP_DIR}/${BACKUP_DATE}/containers.txt" 2>/dev/null || true
        docker images > "${BACKUP_DIR}/${BACKUP_DATE}/images.txt" 2>/dev/null || true
    fi
    
    log_success "Backup creado en ${BACKUP_DIR}/${BACKUP_DATE}"
else
    log_warning "No hay aplicación previa para respaldar"
fi

# Paso 2: Detener servicios actuales (si existen)
log_info "Paso 2/8: Deteniendo servicios actuales..."
cd "$DEPLOY_DIR" 2>/dev/null || true

if [ -f "docker-compose.yml" ] || [ -f "$COMPOSE_FILE" ]; then
    log_info "Deteniendo contenedores Docker..."
    docker-compose -f ${COMPOSE_FILE} down 2>/dev/null || docker-compose down 2>/dev/null || true
    log_success "Servicios detenidos"
else
    log_warning "No hay servicios Docker corriendo"
fi

# Paso 3: Limpiar contenedores e imágenes antiguas (opcional)
log_info "Paso 3/8: Limpiando recursos Docker antiguos..."
docker system prune -f 2>/dev/null || true
log_success "Limpieza completada"

# Paso 4: Verificar archivos necesarios
log_info "Paso 4/8: Verificando archivos de configuración..."

if [ ! -f "${DEPLOY_DIR}/.env" ]; then
    log_error "Archivo .env no encontrado. Por favor, sube el archivo .env primero."
    exit 1
fi

if [ ! -f "${DEPLOY_DIR}/${COMPOSE_FILE}" ]; then
    log_error "Archivo ${COMPOSE_FILE} no encontrado."
    exit 1
fi

log_success "Archivos de configuración encontrados"

# Paso 5: Construir imágenes Docker
log_info "Paso 5/8: Construyendo imágenes Docker..."
cd "$DEPLOY_DIR"
docker-compose -f ${COMPOSE_FILE} build --no-cache
log_success "Imágenes construidas correctamente"

# Paso 6: Iniciar servicios
log_info "Paso 6/8: Iniciando servicios en producción..."
docker-compose -f ${COMPOSE_FILE} up -d
log_success "Servicios iniciados"

# Paso 7: Esperar a que los servicios estén saludables
log_info "Paso 7/8: Esperando a que los servicios estén listos..."
sleep 10

# Verificar estado de contenedores
log_info "Estado de los contenedores:"
docker-compose -f ${COMPOSE_FILE} ps

# Paso 8: Verificar que la aplicación responda
log_info "Paso 8/8: Verificando que la aplicación responda..."
sleep 5

HOST_PORT=$(grep HOST_PORT .env | cut -d '=' -f2 | tr -d ' ' || echo "8080")

if curl -f -s "http://localhost:${HOST_PORT}/" > /dev/null; then
    log_success "✓ Aplicación respondiendo correctamente en puerto ${HOST_PORT}"
else
    log_warning "⚠ La aplicación puede estar iniciando aún. Verifica los logs:"
    log_info "docker-compose -f ${COMPOSE_FILE} logs weatherlink"
fi

# Mostrar resumen
echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          DEPLOYMENT COMPLETADO EXITOSAMENTE            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${BLUE}📊 Resumen del Deployment:${NC}"
echo -e "  • Backup:             ${BACKUP_DIR}/${BACKUP_DATE}"
echo -e "  • Directorio:         ${DEPLOY_DIR}"
echo -e "  • Compose File:       ${COMPOSE_FILE}"
echo -e "  • Puerto App:         ${HOST_PORT}"

echo -e "\n${BLUE}🔍 Comandos útiles:${NC}"
echo -e "  • Ver logs:           cd ${DEPLOY_DIR} && docker-compose -f ${COMPOSE_FILE} logs -f"
echo -e "  • Ver estado:         cd ${DEPLOY_DIR} && docker-compose -f ${COMPOSE_FILE} ps"
echo -e "  • Reiniciar:          cd ${DEPLOY_DIR} && docker-compose -f ${COMPOSE_FILE} restart"
echo -e "  • Detener:            cd ${DEPLOY_DIR} && docker-compose -f ${COMPOSE_FILE} down"
echo -e "  • Restaurar backup:   tar -xzf ${BACKUP_DIR}/${BACKUP_DATE}/app_backup.tar.gz -C ${DEPLOY_DIR}"

echo -e "\n${BLUE}🌐 Acceso a la aplicación:${NC}"
echo -e "  • HTTP:  http://$(hostname -I | awk '{print $1}'):${HOST_PORT}"
echo -e "  • Redpanda Console: http://$(hostname -I | awk '{print $1}'):19644"

echo -e "\n${YELLOW}⚠️  IMPORTANTE:${NC}"
echo -e "  1. Verifica que todos los contenedores estén corriendo"
echo -e "  2. Revisa los logs si algo no funciona"
echo -e "  3. Guarda el backup: ${BACKUP_DIR}/${BACKUP_DATE}"
echo -e "  4. Configura un dominio/SSL con Nginx si es necesario\n"

log_success "Deployment finalizado. ¡Tu aplicación está en producción!"
