# Configuración de Gunicorn para producción
import multiprocessing
import os

# Bind a la dirección local (Nginx hará el proxy)
bind = "0.0.0.0:8000"

# Número de workers (2-4 x número de CPUs)
workers = multiprocessing.cpu_count() * 2 + 1

# Tipo de worker (sync para aplicaciones normales, gevent para async)
worker_class = "sync"

# Timeout para requests largos (especialmente para datos históricos)
timeout = 120

# Nivel de logging
loglevel = "info"

# Logs en Docker se manejan mejor con stdout/stderr
accesslog = "-"
errorlog = "-"

# Capturar salida de stdout/stderr
capture_output = True

# Nombre del proceso
proc_name = "weatherlink_dashboard"

# Reiniciar workers después de este número de requests (previene memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Preload de la aplicación (mejora el tiempo de inicio)
preload_app = True
