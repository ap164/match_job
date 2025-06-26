import json
import io
import os
import struct
import requests
from fastavro import schemaless_reader
from confluent_kafka import Consumer
from pymongo import MongoClient


def load_avro_schema(path="schemas/job_offer_schema.avsc"):
    with open(path, "r") as f:
        return json.load(f)

def get_consumer():
    return Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS_COMMON"),
        "group.id": "raw_offers_group",
        "auto.offset.reset": "earliest"
    })

def get_collection():
    mongo_client = MongoClient(os.environ.get("MONGO_URI"))
    db = mongo_client["kafka_project"]
    return db["kafka_project"]

def decode_confluent_avro(msg_value, avro_schema):
    bytes_io = io.BytesIO(msg_value)
    magic = bytes_io.read(1)
    if magic != b'\x00':
        raise ValueError("Not a Confluent Avro message!")
    schema_id = struct.unpack('>I', bytes_io.read(4))[0]
    return schemaless_reader(bytes_io, avro_schema)

def fetch_exchange_rate(currency):
    try:
        url = f"http://api.nbp.pl/api/exchangerates/rates/A/{currency}/?format=json"
        r = requests.get(url, timeout=3)
        data = r.json()
        return data["rates"][0]["mid"]
    except Exception as e:
        print(f"Błąd pobierania kursu {currency}:", e)
        return None
    

def is_duplicate(record, collection):
    """Sprawdza, czy rekord już istnieje w kolekcji MongoDB."""
    dedup_query = {
        "company": record.get("company"),
        "title": record.get("title"),
        "location": record.get("location"),
        "required_skills": record.get("required_skills")
    }
    return collection.count_documents(dedup_query, limit=1) > 0
