print("=== DEBUG: consumer_main.py start ===", flush=True)
print("🔍 Import start", flush=True)


try:
    print("Import utils...", flush=True)
    from consumer.utils import (
        load_avro_schema,
        get_consumer,
        get_collection,
        decode_confluent_avro,
        is_duplicate)
    print("Import transform...", flush=True)
    from consumer.transform import (
        parse_salary,
        work_mode_normalize,
        parse_experience_level,
        normalize_location,
        normalize_skills,
        normalize_full_contract_type,
        normalize_employment_type)
    print("Importy OK", flush=True)
    
except Exception as e:
    print("❌ Błąd podczas importów:", e, flush=True)
    import traceback
    traceback.print_exc()
def start_consumer_loop(consumer, collection, avro_schema):
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

        # 1.  WYNAGRODZENIE NORMALIZACJA
        record["salary"] = parse_salary(record.get("salary", ""))
        # 2. NORMALIZACJA TRYBU PRACY
        record["work_mode"] = work_mode_normalize(record.get("work_mode", []))
        # 3. NORMALIZACJA POZIOMU DOŚWIADCZENIA
        record["experience_level"] = parse_experience_level(record.get("experience_level", ""))
        # 4. NORMALIZACJA LOKALIZACJI
        record["location"] = normalize_location(record.get("location", ""))
        # 5. NORMALIZACJA WYMAGANYCH UMIEJĘTNOŚCI
        record["required_skills"] = normalize_skills(record.get("required_skills", []))
        # 6. NORMALIZACJA DANYCH O FIRMIE
        record["company"] = record.get("company", "").upper()
        # 7. NORMALIZACJA TYTUŁU OFERTY
        record["title"] = record.get("title", "").upper()
        # 8. NORMALIZACJA TYPU UMOWY
        record["contract_type"] = normalize_full_contract_type(record.get("contract_type", ""), record.get("salary", []))
        # 9. NORMALIZACJA TYPU ZATRUDNIENIA
        record["employment_type"] = normalize_employment_type(record.get("employment_type", ""))
        # 10. DEDUPLIKACJA
        if is_duplicate(record, collection):
            print("⚠️ Duplikat, pomijam:", record.get("title"))
            continue

        # 11. FILTRACJA (stacjonarka)
        work_mode = record.get("work_mode", [])
        if "on-site" in work_mode and ("remote" not in work_mode or "hybrid" not in work_mode) and len(work_mode) == 1:
            print("Filtered out (stacjonarka):", record.get("title"))
            continue

        # 12. FILTRACJA (senior level)
        work_mode = record.get("experience_level", [])
        if "senior" in work_mode and len(work_mode) == 1:
            print("Filtered out (senior lvl):", record.get("title"))
            continue    
        
        # 13. ZAPIS DO MONGO
        collection.insert_one(record)
        print("✔ Wstawiono:", record["title"], "|", record["company"] )



if __name__ == "__main__":
    print("Consumer started!", flush=True)
    try:
        avro_schema = load_avro_schema()
        consumer = get_consumer()
        collection = get_collection()
        consumer.subscribe(["raw_offers"])
        start_consumer_loop(consumer, collection, avro_schema)
    except Exception as e:
        print("❌ Błąd w main:", e, flush=True)
        import traceback
        traceback.print_exc()
