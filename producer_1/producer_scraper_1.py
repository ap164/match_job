import os
import json
import time
import re
import random
import logging
from datetime import datetime, timedelta, timezone

from kafka import KafkaProducer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from confluent_kafka.avro import AvroProducer, loads
from confluent_kafka.avro.cached_schema_registry_client import CachedSchemaRegistryClient

# === Logger configuration ===
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# === Environment variables ===
load_dotenv()
URL_2 = os.getenv("URL_2")
KAFKA_BOOTSTRAP_SERVERS_COMMON = os.getenv("KAFKA_BOOTSTRAP_SERVERS_COMMON")
PRODUCER_CLIENT_ID_2 = os.getenv("PRODUCER_CLIENT_ID_2")
ROW_DATA_TOPIC = os.getenv("ROW_DATA_TOPIC")
LISTINGS_PATH_2 = os.getenv("LISTINGS_PATH_2")
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL")

OFFER_SELECTOR = os.getenv("OFFER_SELECTOR")
TITLE_SELECTOR = os.getenv("TITLE_SELECTOR")
COMPANY_SELECTOR = os.getenv("COMPANY_SELECTOR")
LOCATION_SELECTOR = os.getenv("LOCATION_SELECTOR")
SALARY_SELECTOR = os.getenv("SALARY_SELECTOR")
LINK_SELECTOR = os.getenv("LINK_SELECTOR")
PUBLISHED_SELECTOR = os.getenv("PUBLISHED1_SELECTOR")
TECH_REQUIRED_SELECTOR = os.getenv("TECH_REQUIRED_SELECTOR")
TECH_OPTIONAL_SELECTOR = os.getenv("TECH_OPTIONAL_SELECTOR")
ADDITIONAL_INFO_SELECTOR = os.getenv("ADDITIONAL_INFO_SELECTOR")
LOCATION_PREFIX_1 = os.getenv("LOCATION_PREFIX_1", "")
LOCATION_PREFIX_2 = os.getenv("LOCATION_PREFIX_2", "")


# === Constants ===
POLISH_MONTHS = {
    'stycznia': 1, 'lutego': 2, 'marca': 3, 'kwietnia': 4, 'maja': 5, 'czerwca': 6,
    'lipca': 7, 'sierpnia': 8, 'września': 9, 'października': 10, 'listopada': 11, 'grudnia': 12
}

EXPERIENCE_LEVELS = (
    'asystent', 'praktykant / stażysta', 'młodszy specjalista (junior)',
    'starszy specjalista (senior)', 'specjalista (mid / regular)',
    'ekspert', 'menedżer', 'kierownik / koordynator'
)

CONTRACT_TYPES = (
    'umowa o pracę', 'umowa zlecenie', 'umowa o dzieło',
    'umowa o staż / praktyki', 'umowa o pracę tymczasową',
    'umowa agencyjna', 'umowa na zastępstwo', 'kontrakt b2b'
)

EMPLOYMENT_TYPES = ('pełny etat', 'część etatu', 'dodatkowa / tymczasowa')
WORKPLACE_TYPES = ('praca stacjonarna', 'praca hybrydowa', 'praca zdalna', 'praca mobilna')


# === Helper functions ===

def sleep_random(min_seconds=1, max_seconds=3):
    """Pause execution for a random number of seconds between min_seconds and max_seconds."""
    time.sleep(random.randint(min_seconds, max_seconds))


def parse_published_dt(published_dt_str):
    """Parse a date string containing a Polish month into a timezone-aware datetime object."""
    match = re.search(r'(\d{1,2}) ([a-ząćęłńóśźż]+) (\d{4})', published_dt_str.lower())
    if match:
        day = int(match.group(1))
        month_str = match.group(2)
        month = POLISH_MONTHS.get(month_str)
        year = int(match.group(3))
        if month:
            return datetime(year, month, day, tzinfo=timezone.utc)
    return None


def init_driver():
    """Initialize and return a headless Selenium Chrome WebDriver instance."""
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)


def init_kafka_producer():
    """Initialize and return an Avro Kafka producer based on environment variables."""
    if not all([KAFKA_BOOTSTRAP_SERVERS_COMMON, PRODUCER_CLIENT_ID_2, ROW_DATA_TOPIC, SCHEMA_REGISTRY_URL]):
        raise EnvironmentError("Required environment variables are not set!")
    with open("schemas/key_schema.avsc") as f:
        key_schema_str = f.read()
    with open("schemas/job_offer_schema.avsc") as f:
        value_schema_str = f.read()

    producer = AvroProducer(
        {
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS_COMMON,
            'client.id': PRODUCER_CLIENT_ID_2,
            'schema.registry.url': SCHEMA_REGISTRY_URL,
            'acks': os.getenv('PRODUCER_ACKS', 'all'),
            'compression.type': os.getenv('PRODUCER_COMPRESSION', 'zstd'),
            'linger.ms': int(os.getenv('PRODUCER_LINGER_MS', '50')),
        },
                
                
        default_key_schema=loads(key_schema_str),       
        default_value_schema=loads(value_schema_str)
    )
    return producer, ROW_DATA_TOPIC


def get_offers_from_page(driver, url):
    """Load the given URL and return all job offer elements found on the page."""
    log.info(f"Scraping page: {url}")
    driver.get(url)
    sleep_random(2, 4)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    return soup.select(OFFER_SELECTOR)


def extract_title_company_location(offer):
    """Extract the job title, company name, and location from a job offer element."""
    title = offer.select_one(TITLE_SELECTOR).text.strip()
    company = offer.select_one(COMPANY_SELECTOR).text.strip()
    location = offer.select_one(LOCATION_SELECTOR).text.strip()
    location = location.replace(LOCATION_PREFIX_1, "")
    location = location.replace(LOCATION_PREFIX_2, "")
    return title, company, location


def extract_salary(offer):
    """Extract and clean salary information from a job offer. Returns a list or an empty list."""
    el = offer.select_one(SALARY_SELECTOR)
    row = el.text.strip().replace('\u00A0', '') if el else ''
    return [row] if row else []


def extract_offer_link(offer):
    """Extract the job offer URL from the given offer element."""
    el = offer.select_one(LINK_SELECTOR)
    return el['href'] if el and 'href' in el.attrs else None


def extract_published_date(offer):
    """Extract and parse the job posting's publication date."""
    raw = offer.select_one(PUBLISHED_SELECTOR).text.strip()
    return parse_published_dt(raw)


def extract_offer_tags(offer):
    """Extract additional metadata (e.g. contract type, work mode) from the job offer."""
    items = []
    for i in range(7):
        li = offer.select_one(ADDITIONAL_INFO_SELECTOR.format(i))
        if li:
            items.append(li.text.strip().lower())
    return " ".join(items)


def map_offer_tags_to_categories(info):
    """Map text-based job metadata into structured categories like contract type or work mode."""
    return {
        "experience_level": [x for x in EXPERIENCE_LEVELS if x in info],
        "contract_type": [x for x in CONTRACT_TYPES if x in info],
        "employment_type": [x for x in EMPLOYMENT_TYPES if x in info],
        "work_mode": [x for x in WORKPLACE_TYPES if x in info],
    }


def extract_skills(driver, url):
    """Open the job offer page and extract required and optional technologies."""
    driver.get(url)
    sleep_random(3, 7)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    required = [s.get_text(strip=True) for s in soup.select(TECH_REQUIRED_SELECTOR)]
    optional = [s.get_text(strip=True) + " (optional)" for s in soup.select(TECH_OPTIONAL_SELECTOR)]
    return required + optional


def extract_offer_data(offer, driver, cutoff_time):
    """
    Process a single job offer element and extract all relevant information.

    Returns:
        dict: Job offer data if valid and recent.
        bool: True if the offer is older than the cutoff and scraping should stop.
    """
    try:
        title, company, location = extract_title_company_location(offer)
        salary = extract_salary(offer)
        url = extract_offer_link(offer)
        if not url:
            return None, False

        published = extract_published_date(offer)
        if published < cutoff_time:
            return None, True

        skills = extract_skills(driver, url)
        tags = extract_offer_tags(offer)
        categories = map_offer_tags_to_categories(tags)

        job = {
            "title": title,
            "company": company,
            "location": location,
            "salary_range": salary,
            "link": url,
            "required_skills": skills,
            "employment_type": categories["employment_type"],
            "experience_level": categories["experience_level"],
            "contract_type": categories["contract_type"],
            "work_mode": categories["work_mode"],
            "published_dt": published.isoformat(),
            "scraped_dt": datetime.now(timezone.utc).isoformat()
        }
        return job, False

    except Exception as e:
        log.error(f"Error while processing offer: {e}")
        return None, False


def process_offer_page(driver, producer, topic, key, cutoff, url):
    """
    Process all job offers found on a given listing page.

    Returns:
        bool: True if scraping should stop (due to old data or no offers).
    """
    offers = get_offers_from_page(driver, url)
    if not offers:
        return True

    for offer in offers:
        job, should_stop = extract_offer_data(offer, driver, cutoff)
        if should_stop:
            return True
        if job:
            producer.produce(topic=topic, key=key, value=job)
            log.info(f"Sent to Kafka: {job['title']} @ {job['company']}")
            sleep_random(2, 5)
    return False


def main():
    """Main loop that coordinates scraping job listings and sending them to Kafka."""
    sleep_random(7, 10)
    driver = init_driver()
    producer, topic = init_kafka_producer()
    key = URL_2

    cutoff_time = datetime.now(timezone.utc) - timedelta(days=1)

    page = 1
    while True:
        url = LISTINGS_PATH_2 if page == 1 else f"{LISTINGS_PATH_2}&pn={page}"
        stop = process_offer_page(driver, producer, topic, key, cutoff_time, url)
        if stop:
            break
        page += 1
        sleep_random(15, 20)

    driver.quit()
    producer.flush()


if __name__ == '__main__':
    main()
