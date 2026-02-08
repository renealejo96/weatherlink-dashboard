-- Tabla para registrar eventos de lluvia
CREATE TABLE IF NOT EXISTS rain_events (
    id BIGSERIAL PRIMARY KEY,
    station_key TEXT NOT NULL,
    station_name TEXT NOT NULL,
    event_start TIMESTAMPTZ NOT NULL,
    event_end TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    rain_at_start NUMERIC(10,2),
    rain_at_end NUMERIC(10,2),
    rain_accumulated NUMERIC(10,2),
    max_intensity NUMERIC(10,2),
    duration_minutes INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(station_key, event_start)
);

-- Índices para búsquedas rápidas
CREATE INDEX idx_rain_events_station ON rain_events(station_key);
CREATE INDEX idx_rain_events_active ON rain_events(is_active) WHERE is_active = true;
CREATE INDEX idx_rain_events_start ON rain_events(event_start DESC);

-- Vista de eventos activos
CREATE OR REPLACE VIEW active_rain_events AS
SELECT 
    id,
    station_key,
    station_name,
    event_start,
    rain_at_start,
    rain_accumulated,
    max_intensity,
    EXTRACT(EPOCH FROM (NOW() - event_start))/60 as duration_minutes,
    NOW() - event_start as duration
FROM rain_events
WHERE is_active = true
ORDER BY event_start DESC;

-- Función para cerrar eventos de lluvia automáticamente
CREATE OR REPLACE FUNCTION close_inactive_rain_events()
RETURNS void AS $$
BEGIN
    -- Cerrar eventos que no han tenido actualización en 15 minutos
    UPDATE rain_events
    SET is_active = false,
        event_end = updated_at,
        duration_minutes = EXTRACT(EPOCH FROM (updated_at - event_start))/60
    WHERE is_active = true
      AND updated_at < NOW() - INTERVAL '15 minutes';
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE rain_events IS 'Eventos de lluvia detectados en tiempo real';
COMMENT ON COLUMN rain_events.rain_accumulated IS 'Cantidad de lluvia caída durante este evento (mm)';
COMMENT ON COLUMN rain_events.max_intensity IS 'Máxima intensidad de lluvia durante el evento (mm/hora)';
