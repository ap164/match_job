# 📊 Job Offer Aggregator with Candidate Profile Matching

🇵🇱 Polish version below

## Project Goal

This project aims to **automatically collect job offers** from the most popular job platforms in real time and filter them based on **user-defined preferences**.  

The system:
- searches for job offers,
- filters them by predefined criteria (e.g. **salary range, work mode, contract type**),
- calculates a technical **Skill Match**,
- generates a personalized summary **sent via email**.

The solution saves time and eliminates the need for manually browsing job portals.  
It showcases a **real-world application of data engineering** in the recruitment process.

---

## How It Works (Technical Overview)

### 1. Data Sources – **Kafka Producers (Web Scraping)**

- Two scrapers use **Selenium** and **BeautifulSoup** to periodically gather the latest job offers from various platforms.
- Structured data are sending to the Kafka messaging system.
  
### 2. Data Streaming – **Apache Kafka + Avro**

- Offers are sent to a **Kafka topic** (`raw_offers`).
- Messages are serialized using **Avro** and validated against a schema via **Schema Registry**.

![Screenshot 2025-07-1 at 11 33 25](https://github.com/user-attachments/assets/a694e5cb-62ae-40b4-911e-790b024aca95)

### 3. Stream Processing – **Consumer (Python)**

A Python-based consumer reads and processes incoming messages:

- ✅ **Avro decoding** – according to the defined schema  
- 🔄 **Normalization** – unifying company names, locations, contract types, and experience levels  
- 💱 **Currency conversion** – using **NBP API** to convert salaries to PLN (net/gross, hourly rates)  
- 🧹 **Initial filtering** – e.g. removing duplicates or fully on-site offers  
- 💾 **Data storage in MongoDB** – each offer is saved as a document in a **NoSQL** database

![Screenshot 2025-07-1 at 11 37 23](https://github.com/user-attachments/assets/3c844cea-324a-46be-9bf2-7483399c8b95)

### 4. Analysis & Reporting – **CRON, Pandas, HTML**

A CRON-based analytics module runs periodically (e.g. every 14 days) inside a Docker container:

- 📥 Loads job offers from MongoDB (last 14 days)  
- 🧩 Filters based on user preferences (`requirements_config.yaml`)  
- 🧠 Calculates **Skill Match** – comparing required vs. owned skills (must-have & nice-to-have)  
- 📊 Generates an **HTML report** with the top-matching offers  
- 📬 Sends the report via email (**SMTP**)

<img width="338" alt="Screenshot 2025-07-1 at 11 48 13" src="https://github.com/user-attachments/assets/df9aec37-70ec-4c5c-a6d6-0de60afc3c56" />

---

## Technologies Used

- **Python** – scraping, ETL, data processing (`pandas`, `requests`, `selenium`, `bs4`)
- **Apache Kafka + Avro + Schema Registry** – data streaming & schema validation
- **MongoDB (NoSQL)** – flexible document-based storage
- **Docker + Docker Compose** – containerized architecture
- **CRON** – scheduled task execution in Docker
- **NBP API** – real-time currency conversion to PLN
- **HTML/CSS + SMTP** – HTML report generation and email sending

---

## Summary

This project showcases a **complete real-time data lifecycle**:  
📥 **collection** → 🧪 **validation** → 🔄 **transformation** → 📊 **analysis** → 📧 **reporting**

The system is **modular, scalable, and easily extendable** — for example, to support new job platforms or advanced scoring models.

---

> 🛠️ This project was built for educational and personal skill development purposes only.





# PL: 



# 📊 Agregator ofert pracy z dopasowaniem do wymagań użytkownika

## Cel projektu

Celem projektu jest **automatyczne zbieranie ofert pracy** z najpopularniejszych platform rekrutacyjnych w czasie rzeczywistym oraz filtrowanie ich zgodnie z **preferencjami użytkownika**.  
System:

- przeszukuje ogłoszenia,
- dopasowuje je do zdefiniowanych kryteriów (np. **wynagrodzenie, tryb pracy, forma zatrudnienia**),
- oblicza dopasowanie umiejętności technicznych (**Skill Match**),
- generuje spersonalizowane zestawienie i **wysyła je e-mailem**.

Rozwiązanie oszczędza czas i eliminuje konieczność ręcznego przeszukiwania portali z ogłoszeniami.  
Projekt prezentuje **praktyczne zastosowanie inżynierii danych** w realnym scenariuszu rekrutacyjnym.

---

## Jak to działa (warstwa techniczna)

### 1. Źródła danych – **Producenci Kafka (Web Scraping)**

- Dwa scrapery wykorzystują **Selenium** i **BeautifulSoup**, by okresowo zbierać najnowsze oferty z różnych portali.
- Dane są strukturyzowane i wysyłane do systemu kolejek (Kafka).

### 2. Strumieniowanie danych – **Apache Kafka + Avro**

- Oferty trafiają do **Kafka Topic** (`raw_offers`).
- Komunikaty są serializowane przy użyciu **Avro** i walidowane poprzez **Schema Registry**.
  
![Zrzut ekranu 2025-07-1 o 11 33 25](https://github.com/user-attachments/assets/a694e5cb-62ae-40b4-911e-790b024aca95)

### 3. Przetwarzanie w strumieniu – **Consumer (Python)**

Consumer subskrybuje topic i przetwarza dane:

- ✅ **Dekodowanie Avro** – zgodnie ze schematem danych  
- 🔄 **Normalizacja** – nazwy, lokalizacje, typy umów, poziomy doświadczenia  
- 💱 **Przeliczanie walut** – na podstawie kursu z **API NBP**, stawki w PLN (netto/brutto)  
- 🧹 **Filtrowanie wstępne** – np. usuwanie duplikatów, ofert tylko stacjonarnych  
- 💾 **Zapis do MongoDB** – dane trafiają jako dokumenty do bazy **NoSQL**
  
![Zrzut ekranu 2025-07-1 o 11 37 23](https://github.com/user-attachments/assets/3c844cea-324a-46be-9bf2-7483399c8b95)

### 4. Analiza i raportowanie – **CRON, Pandas, HTML**

Moduł działa cyklicznie (co 14 dni) jako zadanie CRON w kontenerze Docker:

- 📥 Pobiera dane z MongoDB (ostatnie 14 dni)  
- 🧩 Filtrowanie po wymaganiach użytkownika (z pliku `requirements_config.yaml`)  
- 🧠 Oblicza **Skill Match** – analiza zgodności must-have i nice-to-have  
- 📊 Tworzy **raport HTML** z listą najlepiej dopasowanych ofert  
- 📬 Wysyła raport e-mailem do użytkownika (**SMTP**)
  
<img width="338" alt="Zrzut ekranu 2025-07-1 o 11 48 13" src="https://github.com/user-attachments/assets/df9aec37-70ec-4c5c-a6d6-0de60afc3c56" />


---

## Użyte technologie

- **Python** – scraping, ETL, analiza danych (`pandas`, `requests`, `selenium`, `bs4`)
- **Apache Kafka + Avro + Schema Registry** – streaming i kontrola schematów
- **MongoDB (NoSQL)** – elastyczne przechowywanie danych
- **Docker + Docker Compose** – konteneryzacja aplikacji
- **CRON** – harmonogram zadań w kontenerze
- **NBP API** – przeliczanie walut na PLN
- **HTML/CSS + SMTP** – tworzenie i wysyłanie raportów

---

## Podsumowanie

Projekt realizuje **pełny cykl życia danych w czasie rzeczywistym**:  
📥 **pozyskiwanie** → 🧪 **walidacja** → 🔄 **transformacja** → 📊 **analiza** → 📧 **raportowanie**

Rozwiązanie jest **modularne, skalowalne i gotowe do rozszerzeń** — np. o kolejne źródła ofert czy inne modele scoringowe.

---

> 🛠️ Projekt zrealizowany w ramach rozwijania kompetencji i służy wyłącznie celom edukacyjnym.

