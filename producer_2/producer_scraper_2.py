import os
import json
import time
import re
import random
import traceback
import logging
from datetime import datetime, timezone, timedelta

from kafka import KafkaProducer
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from confluent_kafka.avro import AvroProducer, loads
from confluent_kafka.avro.cached_schema_registry_client import CachedSchemaRegistryClient

# === Configure logging ===
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# === Load environment variables ===
load_dotenv()
URL_1 = os.getenv("URL_1")
USER_AGENT_1 = os.getenv("USER_1", "")
LISTINGS_PATH = os.getenv("LISTINGS_PATH")
KAFKA_BOOTSTRAP_SERVERS_COMMON = os.getenv("KAFKA_BOOTSTRAP_SERVERS_COMMON")
PRODUCER_CLIENT_ID_1 = os.getenv("PRODUCER_CLIENT_ID_1")
ROW_DATA_TOPIC = os.getenv("ROW_DATA_TOPIC")
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL")

LISTINGS_CONTAINER_SELECTOR = os.getenv("LISTINGS_CONTAINER_SELECTOR")
OFFER_CARD_SELECTOR = os.getenv("OFFER_CARD_SELECTOR")
DETAILS_CONTAINER_SELECTOR = os.getenv("DETAILS_CONTAINER_SELECTOR")
LOCATION_ICON_SELECTOR = os.getenv("LOCATION_ICON_SELECTOR")
COMPANY_ICON_SELECTOR = os.getenv("COMPANY_ICON_SELECTOR")
PUBLISHED_SELECTOR = os.getenv("PUBLISHED_SELECTOR")
METADATA_BOX_SELECTOR = os.getenv("METADATA_BOX_SELECTOR")
METADATA_TITLE_SELECTOR = os.getenv("METADATA_TITLE_SELECTOR")
METADATA_VALUE_SELECTOR = os.getenv("METADATA_VALUE_SELECTOR")
SKILLS_BOX_SELECTOR = os.getenv("SKILLS_BOX_SELECTOR")
SALARY_BOX_SELECTOR = os.getenv("SALARY_BOX_SELECTOR")
SALARY_MINMAX_SELECTOR = os.getenv("SALARY_MINMAX_SELECTOR")
SALARY_DETAILS_SELECTOR = os.getenv("SALARY_DETAILS_SELECTOR")
UNDISCLOSED_SELECTOR = os.getenv("UNDISCLOSED_SELECTOR")
SALARYTEXT = os.getenv("SALARY_TEXT")
SALARY_RESULT = os.getenv("SALARY_RESULT")

def init_driver() -> webdriver.Chrome:
    """Initialize and return a configured Selenium Chrome WebDriver."""
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    if USER_AGENT_1:
        options.add_argument(f"user-agent={USER_AGENT_1}")
    service = Service("/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=options)



def init_kafka_producer():
    """Initialize and return an Avro Kafka producer based on environment variables."""
    if not all([KAFKA_BOOTSTRAP_SERVERS_COMMON, PRODUCER_CLIENT_ID_1, ROW_DATA_TOPIC, SCHEMA_REGISTRY_URL]):
        raise EnvironmentError("Required environment variables are not set!")

    with open("schemas/key_schema.avsc") as f:
        key_schema_str = f.read()
    with open("schemas/job_offer_schema.avsc") as f:
        value_schema_str = f.read()

    producer = AvroProducer(
        {
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS_COMMON,
            'client.id': PRODUCER_CLIENT_ID_1,
            'schema.registry.url': SCHEMA_REGISTRY_URL
        },
        default_key_schema=loads(key_schema_str),
        default_value_schema=loads(value_schema_str)
    )

    return producer, ROW_DATA_TOPIC

def extract_location(offer) -> str:
    """Extract the job location from the offer card."""
    place_icon = offer.select_one(LOCATION_ICON_SELECTOR)
    if place_icon:
        sibling = place_icon.find_next("span")
        return sibling.get_text(strip=True) if sibling else None
    return None


def extract_offer_link(offer) -> str:
    """Extract and build the full offer link from relative href."""
    anchor = offer.select_one("a.offer-card")
    if anchor and anchor.has_attr("href"):
        return f"{URL_1}{anchor['href']}"
    return None


def extract_offer_details_and_skills(driver, url: str) -> dict:
    """Extract detailed offer metadata and skills from the offer detail page."""
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, DETAILS_CONTAINER_SELECTOR))
    )
    soup = BeautifulSoup(driver.page_source, "html.parser")

    return {
        **extract_metadata(soup),
        "skills": extract_skills(soup),
        "salaries": extract_salaries(soup)
    }


def extract_metadata(soup: BeautifulSoup) -> dict:
    """Extract general job metadata like type of work, experience, etc."""
    mapping = {
        "Type of work": "type_of_work",
        "Experience": "experience",
        "Employment Type": "employment_type",
        "Operating mode": "operating_mode"
    }
    result = {
        "type_of_work": None,
        "experience": None,
        "employment_type": None,
        "operating_mode": None
    }
    for box in soup.select(METADATA_BOX_SELECTOR):
        title = box.select_one(METADATA_TITLE_SELECTOR)
        value = box.select_one(METADATA_VALUE_SELECTOR)
        if title and value:
            key = mapping.get(title.text.strip())
            if key:
                result[key] = [value.text.strip()]
    return result


def extract_skills(soup: BeautifulSoup) -> list:
    """Extract a list of required and optional skills with levels if available."""
    skills = []
    for box in soup.select(SKILLS_BOX_SELECTOR):
        name = box.find("h4")
        level = box.find("span")
        if name:
            skill = name.get_text(strip=True)
            if level:
                skill += f" ({level.get_text(strip=True)})"
            skills.append(skill)
    return skills


def extract_salaries(soup: BeautifulSoup) -> list:
    """Extract salary information as list of strings, including min/max and 'Undisclosed' status."""
    salaries = []

    # Min/max salary + details
    for box in soup.select(SALARY_BOX_SELECTOR):
        minmax = box.select(SALARY_MINMAX_SELECTOR)
        details = box.select_one(SALARY_DETAILS_SELECTOR)

        minmax_text = minmax[0].get_text(strip=True) if minmax else ""
        details_text = details.get_text(strip=True) if details else ""

        if minmax_text and details_text:
            salaries.append(f"{minmax_text} ({details_text})")
        elif minmax_text:
            salaries.append(minmax_text)
        elif details_text:
            salaries.append(details_text)

    # Fallback for "Undisclosed"
    undisclosed = soup.select_one(UNDISCLOSED_SELECTOR)
    if undisclosed and SALARY_TEXT in undisclosed.get_text(strip=True):
        salaries.append(SALARY_RESULT)

    return salaries


def normalize_published_dt(published_dt_raw: str) -> datetime:
    """Normalize the publication date from relative text to absolute UTC datetime."""
    if not published_dt_raw:
        return None
    s = published_dt_raw.strip().lower()
    now = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    parts = s.split(" ")
    if parts[0] == "new":
        return now
    if len(parts) >= 2 and parts[1] in {"day", "days", "days ago"}:
        return now - timedelta(days=int(parts[0]))
    return None


def extract_offer_data(offer, driver) -> dict:
    """Extract and consolidate all job offer data from the listing and detail page."""
    try:
        title_el = offer.select_one("h3")
        company_el = offer.select_one(COMPANY_ICON_SELECTOR)
        published_el = offer.select_one(PUBLISHED_SELECTOR)

        title = title_el.get_text(strip=True) if title_el else "N/A"
        company = company_el.get_text(strip=True) if company_el else "N/A"
        location = extract_location(offer)
        url = extract_offer_link(offer)
        details = extract_offer_details_and_skills(driver, url) if url else {}
        published_dt = normalize_published_dt(published_el.text.strip()) if published_el else None

        return {
            "title": title,
            "company": company,
            "location": location,
            "salary_range": details.get("salaries", []),
            "link": url,
            "required_skills": details.get("skills", []),
            "employment_type": details.get("type_of_work"),
            "experience_level": details.get("experience"),
            "contract_type": details.get("employment_type"),
            "work_mode": details.get("operating_mode"),
            "published_dt": published_dt.isoformat() if published_dt else None,
            "scraped_dt": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        log.error(f"Error parsing job offer: {e}")
        return None

def main():
    """Main entry point: load listings page, extract offers, and send them to Kafka."""
    driver = init_driver()
    url = f"{URL_1}{LISTINGS_PATH}"
    driver.get(url)
    producer, topic = init_kafka_producer()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, LISTINGS_CONTAINER_SELECTOR))
    )

    soup = BeautifulSoup(driver.page_source, "html.parser")
    offer_cards = soup.select(OFFER_CARD_SELECTOR)
    for offer in offer_cards[:200]:
        job_data = extract_offer_data(offer, driver)
        if job_data:
            try:
                producer.produce(
                    topic=topic,
                    key=URL_1,
                    value=job_data
                )
                log.info(f"Sent to Kafka: {job_data['title']} @ {job_data['company']}")
                time.sleep(random.uniform(3, 10))
            except Exception as e:
                log.error(f"Error sending to Kafka: {e}")
                traceback.print_exc()

    producer.flush()
    driver.quit()



if __name__ == "__main__":
    main()
