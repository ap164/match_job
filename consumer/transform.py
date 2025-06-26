import re
from consumer.utils import fetch_exchange_rate

def work_mode_normalize(work_mode):
    """Normalize work mode values and remove duplicates."""
    normalized_modes = []
    seen = set()

    for mode in work_mode:
        if not mode:
            continue  

        mode = mode.lower().strip()

        if "remote" in mode or "zdalna" in mode:
            normalized = "remote"
        elif "hybrid" in mode or "hybrydowa" in mode:
            normalized = "hybrid"
        elif "on-site" in mode or "stacjonarna" in mode:
            normalized = "on-site"
        else:
            normalized = mode  

        if normalized not in seen:
            seen.add(normalized)
            normalized_modes.append(normalized)

    return normalized_modes

def normalize_skills(raw_skills):
    """
    Normalize a nested list of skill strings into a flat list of dictionaries
    with 'skill' and 'level' keys.

    Args:
        raw_skills (list of list of str): e.g. [["Python (regular)", "SQL"], ...]

    Returns:
        list: List of dictionaries, e.g. [{"skill": "python", "level": "regular"}, ...]
    """
    normalized = []
    seen = set()
    if all(isinstance(skill, str) for skill in raw_skills):
        raw_skills = [raw_skills]

    for entry in raw_skills:
        for skill in entry:
            if not skill:
                continue
            match = re.match(r"^(.*?)\s*\((.*?)\)$", skill.strip())
            if match:
                name, level = match.groups()
                name = name.strip().lower()
                level = level.strip().lower()
            else:
                name = skill.strip().lower()
                level = "unspecified"

            key = (name, level)

            if key not in seen:
                seen.add(key)
                normalized.append({
                    "skill": name,
                    "level": level,
                })
    
    return normalized    

def parse_experience_level(text):
    """Normalize experience level values and remove duplicates."""
    normalized_lvl = []
    seen = set()
    if isinstance(text, str):
        text = [text]

    for entry in text:
        if not entry:
            continue

        entry = entry.lower().strip()    

        if "junior" in entry or "młodszy" in entry or "mlodszy" in entry:
            norm = "junior"
        elif "mid" in entry or "regular" in entry:
            norm = "mid"
        elif "senior" in entry or "starszy" in entry:
            norm = "senior"
        else:
            norm = entry

        if norm not in seen:
            seen.add(norm)
            normalized_lvl.append(norm)
    return normalized_lvl

def normalize_location(entry):
    """
    Normalize location string into a structured dictionary.

    Args:
        entry (str or list): Location information.

    Returns:
        dict: Dictionary with keys 'remote', 'city', and 'district'.
    """
    if not entry:
        return {"remote": False, "city": None, "district": None}

    if isinstance(entry, list):
        entry = " ".join(entry)

    result = {
        "remote": False,
        "city": None,
        "district": None
    }

    if not entry:
        return result

    # Detect remote work
    if re.search(r"(praca zdalna|cała polska|remote work|entire poland|fully remote)", entry, flags=re.IGNORECASE):
        result["remote"] = True

    location_part = entry
    # Try to extract city and district
    match = re.search(r"(?:praca zdalna\)?)\s*(.*)", entry, flags=re.IGNORECASE)
    if match:
        location_part = match.group(1).strip()

    # Split by comma
    parts = [part.strip() for part in location_part.split(",")]

    if len(parts) == 1 and parts[0]:
        result["city"] = parts[0]
    elif len(parts) >= 2:
        result["city"] = parts[0]
        result["district"] = ", ".join(parts[1:])

    return result

def parse_salary(texts):
    """
    Parse salary information from text(s) and normalize to PLN per hour.

    Args:
        texts (str or list): Salary string(s).

    Returns:
        list: List of dictionaries with salary details.
    """
    results = []

    if not isinstance(texts, list):
        texts = [texts]

    for text in texts:
        result = {
            "min": None,
            "max": None,
            "currency": None,
            "unit": "hour",  # always hourly after conversion
            "net_gross": None,
            "contract": None
        }

        if not isinstance(text, str) or not text.strip():
            results.append(result)
            continue

        # Replace EN DASH, EM DASH with minus
        text = text.replace('–', '-').replace('—', '-')  

        # Find salary range
        match = re.search(r'([\d\s]+)[–-]([\d\s]+)', text)
        if match:
            min_val = int(match.group(1).replace(' ', ''))
            max_val = int(match.group(2).replace(' ', ''))

            # Monthly or hourly?
            is_monthly = bool(re.search(r'mies|miesięcz|month', text.lower()))
            is_hourly = bool(re.search(r'godz|/h|hour', text.lower()))

            if is_monthly:
                result["min"] = round(min_val / 160, 2)
                result["max"] = round(max_val / 160, 2)
            elif is_hourly:
                result["min"] = min_val
                result["max"] = max_val

        # Detect currency
        if "€" in text or "eur" in text.lower():
            result["currency"] = "EUR"
        elif "$" in text or "usd" in text.lower():
            result["currency"] = "USD"
        elif "zł" in text.lower() or "pln" in text.lower():
            result["currency"] = "PLN"
        elif "£" in text or "gbp" in text.lower():
            result["currency"] = "GBP"

        # Convert to PLN if needed
        if result["currency"] in ["EUR", "USD", "GBP"]:
            rate = fetch_exchange_rate(result["currency"])
            if rate and result["min"] is not None:
                result["min"] = round(result["min"] * rate, 2)
                result["max"] = round(result["max"] * rate, 2)
                result["currency"] = "PLN"

        # Detect net/gross
        if "net" in text.lower() or "netto" in text.lower():
            result["net_gross"] = "net"
        elif "gross" in text.lower() or "brutto" in text.lower():
            result["net_gross"] = "gross"

        # Detect contract type
        if "b2b" in text.lower() or "(+vat)" in text.lower():
            result["contract"] = "b2b"
        elif "permanent" in text.lower():
            result["contract"] = "permanent"
        elif "mandate" in text.lower():
            result["contract"] = "mandate"    
        elif "any" in text.lower():
            result["contract"] = "any"
            
        results.append(result)

    return results

def normalize_employment_type(employment_type):
    """
    Normalize employment type (full-time / part-time).

    Args:
        employment_type (str): Employment type string.

    Returns:
        dict or None: Dictionary with employment type flags or None.
    """
    employment_types = {"full_time": False, "part_time": False}

    if not employment_type or not isinstance(employment_type, str) or not employment_type.strip():
        return None  

    text = employment_type.lower().strip()

    if any(kw in text for kw in ["full", "pełny", "pelny"]):
        employment_types["full_time"] = True

    if any(kw in text for kw in ["part", "część", "czesc", "dodatkowa", "tymczasow"]):
        employment_types["part_time"] = True

    if not employment_types["full_time"] and not employment_types["part_time"]:
        employment_types["other"] = text

    return employment_types

def normalize_contract_type(contract_type):
    """
    Normalize contract type.

    Args:
        contract_type (str): Contract type string.

    Returns:
        dict or None: Dictionary with contract type flags or None.
    """
    if not contract_type or not isinstance(contract_type, str) or not contract_type.strip():
        return None
    contract_types = {"permanent": False, "b2b": False, "mandate": False}

    contract_type = contract_type.lower().strip()

    if "b2b" in contract_type or "business to business" in contract_type:
        contract_types["b2b"] = True
    if "umowa o pracę" in contract_type or "employment contract" in contract_type or "permanent" in contract_type or "umowa o prace" in contract_type:
        contract_types["permanent"] = True
    if "umowa zlecenie" in contract_type or "contract of mandate" in contract_type:
        contract_types["mandate"] = True
    if "any" in contract_type:
        contract_types = {k: True for k in contract_types}

    return contract_types

def salary_option_vs_contract_type(salary_list, contract_types):
    """
    Update contract types based on salary contract information.

    Args:
        salary_list (list): List of salary dictionaries.
        contract_types (dict): Contract type flags.

    Returns:
        dict: Updated contract type flags.
    """
    for entry in salary_list:
        salary_contract_type = entry.get("contract")
        if salary_contract_type == "b2b":
            contract_types["b2b"] = True
        elif salary_contract_type == "permanent":
            contract_types["permanent"] = True
        elif salary_contract_type == "mandate":
            contract_types["mandate"] = True
        elif salary_contract_type == "any":
            contract_types = {k: True for k in contract_types}
    return contract_types

def normalize_full_contract_type(declared_contract_type, salary_list):
    """
    Combine contract type information from job offer and salary section.

    Args:
        declared_contract_type (str): Declared contract type.
        salary_list (list): List of salary dictionaries.

    Returns:
        dict or None: Combined contract type flags or None.
    """
    if not declared_contract_type and not salary_list:
        return None

    normalized = normalize_contract_type(declared_contract_type)
    if normalized is None:
        normalized = {"permanent": False, "b2b": False, "mandate": False}

    if not salary_list:
        return normalized

    return salary_option_vs_contract_type(salary_list, normalized)
