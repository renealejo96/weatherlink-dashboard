import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from kafka import KafkaProducer
from weatherlink_client import WeatherLinkClient


def create_clients():
    """Create WeatherLink clients for configured stations from environment."""
    stations = {
        'finca1': {
            'name': 'PYGANFLOR',
            'api_key': os.getenv('FINCA1_API_KEY'),
            'api_secret': os.getenv('FINCA1_API_SECRET'),
            'station_id': os.getenv('FINCA1_STATION_ID'),
        },
        'finca2': {
            'name': 'Urcuquí',
            'api_key': os.getenv('FINCA2_API_KEY'),
            'api_secret': os.getenv('FINCA2_API_SECRET'),
            'station_id': os.getenv('FINCA2_STATION_ID'),
        },
        'finca3': {
            'name': 'Malchinguí',
            'api_key': os.getenv('FINCA3_API_KEY'),
            'api_secret': os.getenv('FINCA3_API_SECRET'),
            'station_id': os.getenv('FINCA3_STATION_ID'),
        },
    }

    clients = {}
    for key, s in stations.items():
        if s['api_key'] and s['api_secret'] and s['station_id']:
            clients[key] = {
                'meta': s,
                'client': WeatherLinkClient(s['api_key'], s['api_secret'], s['station_id']),
            }
    return clients


def build_producer(bootstrap_servers: str):
    return KafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8'),
        linger_ms=50,
        request_timeout_ms=120000,  # 120 segundos
        max_block_ms=180000,  # 180 segundos max para metadata
        retries=5,
        acks='all',
    )


def main():
    load_dotenv()

    bootstrap = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    topic = os.getenv('KAFKA_TOPIC_RAW', 'weatherlink.raw')
    poll_interval = int(os.getenv('POLL_INTERVAL_SEC', '60'))

    producer = build_producer(bootstrap)
    clients = create_clients()

    if not clients:
        raise RuntimeError('No hay estaciones configuradas correctamente en .env')

    print(f"⏳ Publicando datos en Kafka cada {poll_interval}s → {topic} (broker: {bootstrap})")
    while True:
        for station_key, entry in clients.items():
            wl = entry['client']
            meta = entry['meta']
            try:
                data = wl.get_current_conditions()
                event = {
                    'station_key': station_key,
                    'station_name': meta['name'],
                    'station_id': meta['station_id'],
                    'ingest_ts': int(time.time()),
                    'event_ts': data.get('timestamp'),
                    'payload': data,
                }
                producer.send(topic, key=station_key, value=event)
                print(f"✔ [{datetime.now().isoformat()}] Enviado {station_key} ts={event['event_ts']}")
            except Exception as e:
                print(f"⚠ Error obteniendo/enviando datos de {station_key}: {e}")
        producer.flush()
        time.sleep(poll_interval)


if __name__ == '__main__':
    main()
