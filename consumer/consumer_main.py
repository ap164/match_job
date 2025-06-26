from consumer.utils import (
    load_avro_schema,
    get_consumer,
    get_collection,
    decode_confluent_avro,
    is_duplicate)

from consumer.transform import (
    parse_salary,
    work_mode_normalize,
    parse_experience_level,
    normalize_location,
    normalize_skills,
    normalize_full_contract_type,
    normalize_employment_type)
    

def start_consumer_loop(consumer, collection, avro_schema):
    """
    Main loop for consuming Kafka messages, transforming, filtering, and saving them to MongoDB.

    Args:
        consumer (Consumer): Kafka Consumer instance.
        collection (Collection): MongoDB collection to store records.
        avro_schema (dict): Avro schema for decoding messages.
    """
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            print("Kafka error:", msg.error())
            continue

        try:
            record = decode_confluent_avro(msg.value(), avro_schema)
        except Exception as e:
            print("Avro decode error:", e, flush=True)
            continue

        # 1. SALARY NORMALIZATION
        record["salary"] = parse_salary(record.get("salary", ""))
        # 2. WORK MODE NORMALIZATION
        record["work_mode"] = work_mode_normalize(record.get("work_mode", []))
        # 3. EXPERIENCE LEVEL NORMALIZATION
        record["experience_level"] = parse_experience_level(record.get("experience_level", ""))
        # 4. LOCATION NORMALIZATION
        record["location"] = normalize_location(record.get("location", ""))
        # 5. REQUIRED SKILLS NORMALIZATION
        record["required_skills"] = normalize_skills(record.get("required_skills", []))
        # 6. COMPANY NAME NORMALIZATION
        record["company"] = record.get("company", "").upper()
        # 7. JOB TITLE NORMALIZATION
        record["title"] = record.get("title", "").upper()
        # 8. CONTRACT TYPE NORMALIZATION
        record["contract_type"] = normalize_full_contract_type(record.get("contract_type", ""), record.get("salary", []))
        # 9. EMPLOYMENT TYPE NORMALIZATION
        record["employment_type"] = normalize_employment_type(record.get("employment_type", ""))
        # 10. DEDUPLICATION
        if is_duplicate(record, collection):
            print("⚠️ Duplicate, skipping:", record.get("title"))
            continue

        # 11. FILTERING (on-site)
        work_mode = record.get("work_mode", [])
        if "on-site" in work_mode and ("remote" not in work_mode or "hybrid" not in work_mode) and len(work_mode) == 1:
            print("Filtered out (on-site):", record.get("title"))
            continue

        # 12. FILTERING (NO senior level)
        experience_level = record.get("experience_level", [])
        if "senior" in experience_level and len(experience_level) == 1:
            print("Filtered out (senior level):", record.get("title"))
            continue    
        
        # 13. SAVE TO MONGO
        collection.insert_one(record)
        print("✔ Inserted:", record["title"], "|", record["company"] )


if __name__ == "__main__":
    """
    Entry point for the Kafka consumer script.
    Loads schema, initializes consumer and MongoDB, and starts the main loop.
    """
    print("Consumer started!", flush=True)
    try:
        avro_schema = load_avro_schema()
        consumer = get_consumer()
        collection = get_collection()
        consumer.subscribe(["raw_offers"])
        start_consumer_loop(consumer, collection, avro_schema)
    except Exception as e:
        print("Error in main:", e, flush=True)
        import traceback
        traceback.print_exc()
