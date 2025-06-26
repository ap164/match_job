import json
import io
import os
import struct
import requests
from fastavro import schemaless_reader
from confluent_kafka import Consumer
from pymongo import MongoClient


def load_avro_schema(path="schemas/job_offer_schema.avsc"):
    """Load an Avro schema from a given file path."""
    with open(path, "r") as f:
        return json.load(f)

def get_consumer():
    """Create and return a Kafka Consumer instance using environment variables """
    return Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS_COMMON"),
        "group.id": "raw_offers_group",
        "auto.offset.reset": "earliest"
    })

def get_collection():
    """Connect to MongoDB and return the target collection"""
    mongo_client = MongoClient(os.environ.get("MONGO_URI"))
    db = mongo_client["kafka_project"]
    return db["kafka_project"]

def decode_confluent_avro(msg_value, avro_schema):
    """Decode a Confluent Avro message using the provided schema.

    Args:
        msg_value (bytes): Raw message value from Kafka.
        avro_schema (dict): Avro schema for decoding.

    Returns:
        dict: Decoded message as a dictionary.

    Raises:
        ValueError: If the message is not in Confluent Avro format.
    """
    bytes_io = io.BytesIO(msg_value)
    magic = bytes_io.read(1)
    if magic != b'\x00':
        raise ValueError("Not a Confluent Avro message!")
    schema_id = struct.unpack('>I', bytes_io.read(4))[0]
    return schemaless_reader(bytes_io, avro_schema)

def fetch_exchange_rate(currency):
    """
    Fetch the current exchange rate for a given currency to PLN.

    Args:
        currency (str): Currency code (e.g., 'EUR', 'USD').

    Returns:
        float or None: Exchange rate or None if fetching fails.
    """
    try:
        url = f"http://api.nbp.pl/api/exchangerates/rates/A/{currency}/?format=json"
        r = requests.get(url, timeout=3)
        data = r.json()
        return data["rates"][0]["mid"]
    except Exception as e:
        print(f"Error fetching exchange rate for {currency}:", e)
        return None
    

def is_duplicate(record, collection):
    """
    Check if a given record already exists in the MongoDB collection.

    Args:
        record (dict): Job offer record to check.
        collection (Collection): MongoDB collection object.

    Returns:
        bool: True if duplicate exists, False otherwise.
    """
    dedup_query = {
        "company": record.get("company"),
        "title": record.get("title"),
        "location": record.get("location"),
        "required_skills": record.get("required_skills")
    }
    return collection.count_documents(dedup_query, limit=1) > 0
