import os
import time
import random
import traceback
import logging
from datetime import datetime, timezone

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from confluent_kafka.avro import AvroProducer, loads

# === Configure logging ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

# === Load environment variables ===
load_dotenv()
URL_1 = os.getenv("URL_1")
LISTINGS_PATH = os.getenv("LISTINGS_PATH")
KAFKA_BOOTSTRAP_SERVERS_COMMON = os.getenv("KAFKA_BOOTSTRAP_SERVERS_COMMON")
PRODUCER_CLIENT_ID_1 = os.getenv("PRODUCER_CLIENT_ID_1")
ROW_DATA_TOPIC = os.getenv("ROW_DATA_TOPIC")
SCHEMA_REGISTRY_URL = os.getenv("SCHEMA_REGISTRY_URL")
DETAILS_CONTAINER_SELECTOR = os.getenv("DETAILS_CONTAINER_SELECTOR")
COMPANY_SELECTOR = os.getenv("COMPANY_ICON_SELECTOR")
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
OFFER_SELLECTOR_SCROLL = os.getenv("OFFER_SELLECTOR_SCROLL")
OFFER_CARD_SELECTOR = os.getenv("OFFER_CARD_SELECTOR")
DRIVER_EXECUTE_SCRIPT = os.getenv("DRIVER_EXECUTE_SCRIPT")
TITLE_SELECTOR1 = os.getenv("TITLE_SELECTOR1")
COMPANY_SVG_SELECTOR = os.getenv("COMPANY_SVG_SELECTOR")
COMPANY_NAME_SELECTOR = os.getenv("COMPANY_NAME_SELECTOR")
LOCATION_PRIMARY_SELECTOR = os.getenv("LOCATION_PRIMARY_SELECTOR")
LOCATION_MULTILOCATION_BUTTON_SELECTOR = os.getenv("LOCATION_MULTILOCATION_BUTTON_SELECTOR")
LOCATION_MULTILOCATION_SPAN_SELECTOR = os.getenv("LOCATION_MULTILOCATION_SPAN_SELECTOR")
LOCATION_SELECTOR = os.getenv("LOCATION_ICON_SELECTOR")  
PRODUCER_ACKS = os.getenv('PRODUCER_ACKS', 'all')
PRODUCER_COMPRESSION = os.getenv('PRODUCER_COMPRESSION', 'zstd')
PRODUCER_LINGER_MS = int(os.getenv('PRODUCER_LINGER_MS', '50'))

def init_driver() -> webdriver.Chrome:
    options = Options()
    options.binary_location = "/usr/bin/chromium"
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    service = Service("/usr/bin/chromedriver")
    log.info("Initialized Chrome WebDriver.")
    return webdriver.Chrome(service=service, options=options)

def init_kafka_producer():
    log.info("Initializing Kafka producer...")
    if not all([KAFKA_BOOTSTRAP_SERVERS_COMMON, PRODUCER_CLIENT_ID_1, ROW_DATA_TOPIC, SCHEMA_REGISTRY_URL]):
        log.error("Missing required environment variables for Kafka producer!")
        raise EnvironmentError("Required environment variables are not set!")
    with open("schemas/key_schema.avsc") as f:
        key_schema_str = f.read()
    with open("schemas/job_offer_schema.avsc") as f:
        value_schema_str = f.read()

    producer = AvroProducer(
        {
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS_COMMON,
            'client.id': PRODUCER_CLIENT_ID_1,
            'schema.registry.url': SCHEMA_REGISTRY_URL,
            'acks': PRODUCER_ACKS,
            'compression.type': PRODUCER_COMPRESSION,
            'linger.ms': PRODUCER_LINGER_MS,
        },
        default_key_schema=loads(key_schema_str),
        default_value_schema=loads(value_schema_str)
    )
    log.warning("AvroProducer is deprecated — consider migrating to AvroSerializer.")
    return producer, ROW_DATA_TOPIC

def extract_title(soup):
    title = soup.select_one(TITLE_SELECTOR1)
    return title.get_text(strip=True) if title else ""




def extract_company(soup):
    company_svg = soup.select_one(COMPANY_SVG_SELECTOR)
    if company_svg:
        parent = company_svg.parent
        if parent:
            h2 = parent.select_one(COMPANY_NAME_SELECTOR)
            if h2:
                return h2.get_text(strip=True)
    return None

def extract_location(soup):
    button = soup.select_one(LOCATION_MULTILOCATION_BUTTON_SELECTOR)
    if button:
        main_loc_span = button.select_one(LOCATION_MULTILOCATION_SPAN_SELECTOR)
        if main_loc_span:
            return main_loc_span.get_text(strip=True)
    span = soup.select_one(LOCATION_PRIMARY_SELECTOR)
    if span:
        return span.get_text(strip=True)
    location = soup.select_one(LOCATION_SELECTOR)
    return location.get_text(strip=True) if location else None

def extract_published(soup):
    published = soup.select_one(PUBLISHED_SELECTOR)
    if not published:
        return None
    published_text = published.get_text(strip=True)
    if published_text.lower() == "new":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return published_text

def clean_value_to_list(val):
    """helper for extract_metadata"""
    if not val:
        return []
    val = val.strip()
    if ',' in val:
        return [v.strip() for v in val.split(',') if v.strip()]
    return [val] if val else []

def extract_metadata(soup: BeautifulSoup) -> dict:
    mapping = {
        "Type of work": "type_of_work",
        "Experience": "experience",
        "Employment Type": "employment_type",
        "Operating mode": "operating_mode"
    }
    result = {v: [] for v in mapping.values()}
    for box in soup.select(METADATA_BOX_SELECTOR):
        title = box.select_one(METADATA_TITLE_SELECTOR)
        value = box.select_one(METADATA_VALUE_SELECTOR)
        if title and value:
            key = mapping.get(title.text.strip())
            if key:
                result[key] = clean_value_to_list(value.text)
    return result

def extract_skills(soup: BeautifulSoup) -> list:
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
    salaries = []
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
    undisclosed = soup.select_one(UNDISCLOSED_SELECTOR)
    if undisclosed and SALARYTEXT in undisclosed.get_text(strip=True):
        salaries.append(SALARY_RESULT)
    return salaries

def extract_offer_details_and_skills(driver, url: str) -> dict:
    try:
        log.info(f"Opening offer detail page: {url}")
        driver.get(url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, DETAILS_CONTAINER_SELECTOR))
        )
        soup = BeautifulSoup(driver.page_source, "html.parser")
        metadata = extract_metadata(soup)
        return {
            "title": extract_title(soup),
            "company": extract_company(soup),
            "location": extract_location(soup),
            "salary_range": extract_salaries(soup),
            "link": url,
            "required_skills": extract_skills(soup),
            "employment_type": metadata.get("type_of_work", []),
            "experience_level": metadata.get("experience", []),
            "contract_type": metadata.get("employment_type", []),
            "work_mode": metadata.get("operating_mode", []),
            "published_dt": extract_published(soup),
            "scraped_dt": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        log.error(f"Failed to extract details for {url}: {e}")
        traceback.print_exc()
        return {}

def scroll_to_bottom_and_collect_offers(driver, offer_selector=OFFER_SELLECTOR_SCROLL, pause_time=10.0, max_scrolls=10000, patience=5, logger=None):
    from selenium.webdriver.common.by import By
    logger = logger or logging.getLogger(__name__)
    seen_links = set()
    scroll_count = 0
    no_increase = 0

    while scroll_count < max_scrolls:
        offers = driver.find_elements(By.CSS_SELECTOR, offer_selector)
        new_links = set()
        for offer in offers:
            try:
                href = offer.get_attribute("href")
                if href:
                    new_links.add(href)
            except Exception:
                continue

        prev_count = len(seen_links)
        seen_links.update(new_links)
        logger.info(f"[SCOLL: {scroll_count}] unique urls: {len(seen_links)}, seem now: {len(new_links)}")

        driver.execute_script(DRIVER_EXECUTE_SCRIPT)
        time.sleep(pause_time)
        if len(seen_links) == prev_count:
            no_increase += 1
            if no_increase >= patience:
                logger.info("NO MORE OFFERS. STOP SCROLLING NOW")
                break
        else:
            no_increase = 0

        scroll_count += 1

    logger.info(f"NUMBER OF UNIQUE OFFERS: {len(seen_links)} ")
    return seen_links

def main():
    driver = init_driver()
    url = f"{URL_1}{LISTINGS_PATH}"
    log.info(f"Loading listing page: {url}")
    driver.get(url)
    time.sleep(10)
    producer, topic = init_kafka_producer()

    all_links = scroll_to_bottom_and_collect_offers(driver, offer_selector=OFFER_CARD_SELECTOR, pause_time=2)
    log.info(f"ALL: {len(all_links)} UNIQUE OFFERS")


    for url in list(all_links)[:200]:
        try:
            details = extract_offer_details_and_skills(driver, url)
            if not details.get("title"):
                log.error(f"NO TITLE FOR {url}")
                continue
            # Avro: location (null/string), published_dt (null/string)
            if details["location"] is not None and not isinstance(details["location"], str):
                details["location"] = str(details["location"])
            if details["published_dt"] is not None and not isinstance(details["published_dt"], str):
                details["published_dt"] = str(details["published_dt"])
            producer.produce(
                topic=topic,
                key=URL_1,
                value=details
            )
            log.info(f"SEND to Kafka: {details['title']} @ {details.get('company', '-')}")
            time.sleep(random.uniform(3, 10))
        except Exception as e:
            log.error(f"error: {url}: {e}")
            traceback.print_exc()
        time.sleep(7)

if __name__ == "__main__":
    main()
