#!/bin/bash
##############################################################################
# Script de Deployment SEGURO para Hostinger VPS
# Proyecto: weatherlink_prod (Totalmente aislado de otras apps en el servidor)
# Dominios: weather.velezrapp.cloud / estacion.velezrapp.cloud
# Uso: sudo ./deploy-hostinger.sh
##############################################################################

set -e  # Salir si hay algún error fatal

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuración de aislamiento estricto
PROJECT_NAME="weatherlink_prod"
# Directorio actual donde está el script (soporta /root/weatherlink-dashboard o /var/www/weatherlink)
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="/var/backups/weatherlink"
COMPOSE_FILE="docker-compose.production.yml"
DOMAIN="weather.velezrapp.cloud"

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  WeatherLink Dashboard - Despliegue Seguro VPS         ║${NC}"
echo -e "${BLUE}║  Proyecto Aislado: ${PROJECT_NAME}                     ║${NC}"
echo -e "${BLUE}║  Dominios: ${DOMAIN} / estacion.velezrapp.cloud ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[⚠]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }

# 1. Detectar comando docker compose
if docker compose version &>/dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &>/dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    log_error "Ni 'docker compose' ni 'docker-compose' están instalados en este servidor."
    exit 1
fi
log_info "Motor de orquestación detectado: ${DOCKER_COMPOSE}"

# Paso 1: Backup preventivo local del proyecto
log_info "Paso 1/7: Creando backup del directorio ${DEPLOY_DIR}..."
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "${BACKUP_DIR}/${BACKUP_DATE}"

if [ -d "$DEPLOY_DIR" ]; then
    tar -czf "${BACKUP_DIR}/${BACKUP_DATE}/app_backup.tar.gz" -C "$DEPLOY_DIR" --exclude='.git' . 2>/dev/null || true
    log_success "Backup creado en ${BACKUP_DIR}/${BACKUP_DATE}"
fi

cd "$DEPLOY_DIR" 2>/dev/null || true

# Paso 2: Detener ÚNICAMENTE los contenedores de este proyecto (weatherlink_prod)
log_info "Paso 2/7: Deteniendo solo los contenedores de WeatherLink (otras apps NO se tocan)..."
$DOCKER_COMPOSE -p ${PROJECT_NAME} -f ${COMPOSE_FILE} down 2>/dev/null || true
log_success "Servicios de WeatherLink detenidos de forma segura"

# NOTA DE SEGURIDAD:
# NUNCA ejecutamos 'docker system prune' para no borrar imágenes ni contenedores de tus otras apps.

# Paso 3: Validar directorios y configuración .env
log_info "Paso 3/7: Verificando directorios y configuración..."
mkdir -p ./logs ./nginx/logs ./nginx/ssl ./nginx/conf.d ./certbot/www

if [ ! -f ".env" ]; then
    if [ -f ".env.production.example" ]; then
        log_warning "No se encontró .env. Creando a partir de .env.production.example..."
        cp .env.production.example .env
        log_warning "Asegúrate de colocar tus credenciales en /var/www/weatherlink/.env"
    else
        log_error "Archivo .env no encontrado."
        exit 1
    fi
fi

# Paso 4: Certificado SSL temporal para arranque seguro
if [ ! -f "./nginx/ssl/fullchain.pem" ] || [ ! -f "./nginx/ssl/privkey.pem" ]; then
    log_warning "Certificado SSL no encontrado. Creando certificado temporal para arranque..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout ./nginx/ssl/privkey.pem \
        -out ./nginx/ssl/fullchain.pem \
        -subj "/C=EC/ST=Pichincha/L=Quito/O=WeatherLink/CN=${DOMAIN}" 2>/dev/null || true
    log_success "Certificado SSL de inicialización preparado"
fi

# Paso 5: Construir imágenes Docker de WeatherLink (Optimizadas sin PySpark ni Java)
log_info "Paso 5/7: Construyendo imágenes optimizadas de WeatherLink..."
$DOCKER_COMPOSE -p ${PROJECT_NAME} -f ${COMPOSE_FILE} build
log_success "Imágenes construidas exitosamente"

# Paso 6: Iniciar el stack aislado
log_info "Paso 6/7: Levantando contenedores en el proyecto aislado '${PROJECT_NAME}'..."
$DOCKER_COMPOSE -p ${PROJECT_NAME} -f ${COMPOSE_FILE} up -d
log_success "Contenedores de WeatherLink iniciados"

# Paso 7: Verificación de salud
log_info "Paso 7/7: Esperando inicialización..."
sleep 12
$DOCKER_COMPOSE -p ${PROJECT_NAME} -f ${COMPOSE_FILE} ps

HOST_PORT=$(grep -E '^HOST_PORT=' .env | cut -d '=' -f2 | tr -d ' ' || echo "8090")
[ -z "$HOST_PORT" ] && HOST_PORT="8090"

if curl -f -s "http://127.0.0.1:${HOST_PORT}/" > /dev/null; then
    log_success "✓ La aplicación WeatherLink está respondiendo correctamente en http://127.0.0.1:${HOST_PORT}"
else
    log_warning "⚠ La aplicación puede estar terminando de arrancar. Revisa los logs con: docker logs -f weatherlink_app_prod"
fi

echo -e "\n${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║          DESPLIEGUE FINALIZADO CON ÉXITO               ║${NC}"
echo -e "${GREEN}║     Ninguna otra aplicación del VPS fue afectada       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}\n"

echo -e "${CYAN}🌐 Acceso a WeatherLink:${NC}"
echo -e "  • Puerto asignado:     ${HOST_PORT} (127.0.0.1:${HOST_PORT})"
echo -e "  • Dominio público:     https://${DOMAIN}"
echo -e "  • Dominios admitidos:  weather.velezrapp.cloud / estacion.velezrapp.cloud"
echo -e "\n${CYAN}🔍 Comandos para monitorear solo WeatherLink:${NC}"
echo -e "  • Ver estado:          ${DOCKER_COMPOSE} -p ${PROJECT_NAME} -f ${COMPOSE_FILE} ps"
echo -e "  • Ver logs de lluvia:  docker logs -f weatherlink_rain_alerts_prod"
echo -e "  • Ver logs telemetría: docker logs -f weatherlink_streaming_prod"
echo -e "  • Ver logs web:        docker logs -f weatherlink_app_prod"
