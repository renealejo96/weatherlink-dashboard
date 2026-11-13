#!/bin/bash
##############################################################################
# Script para emitir certificado Let's Encrypt SSL
# Soporta: weather.velezrapp.cloud y estacion.velezrapp.cloud
# Uso: sudo ./setup_ssl.sh [tu-email@correo.com]
##############################################################################

set -e

PRIMARY_DOMAIN="weather.velezrapp.cloud"
ALT_DOMAIN="estacion.velezrapp.cloud"
EMAIL=${1:-"admin@velezrapp.cloud"}

echo "🔒 Solicitando certificado SSL para: ${PRIMARY_DOMAIN} y ${ALT_DOMAIN}"
echo "📧 Email de contacto: ${EMAIL}"

mkdir -p ./certbot/www ./nginx/ssl

docker run -it --rm \
    -v "$(pwd)/certbot/www:/var/www/certbot" \
    -v "/etc/letsencrypt:/etc/letsencrypt" \
    certbot/certbot certonly --webroot \
    --webroot-path=/var/www/certbot \
    -d "${PRIMARY_DOMAIN}" \
    -d "${ALT_DOMAIN}" \
    --email "${EMAIL}" \
    --agree-tos \
    --non-interactive || true

if [ -f "/etc/letsencrypt/live/${PRIMARY_DOMAIN}/fullchain.pem" ]; then
    cp "/etc/letsencrypt/live/${PRIMARY_DOMAIN}/fullchain.pem" ./nginx/ssl/fullchain.pem
    cp "/etc/letsencrypt/live/${PRIMARY_DOMAIN}/privkey.pem" ./nginx/ssl/privkey.pem
    chmod 600 ./nginx/ssl/privkey.pem
    
    if docker ps | grep -q weatherlink_nginx_prod; then
        docker exec weatherlink_nginx_prod nginx -s reload
        echo "✅ Nginx recargado con el certificado de Let's Encrypt!"
    fi
    echo "🎉 ¡SSL activo en https://${PRIMARY_DOMAIN} y https://${ALT_DOMAIN}!"
else
    echo "ℹ️ Si no se pudo emitir de inmediato, Nginx continúa funcionando de forma segura con el certificado de arranque."
fi
