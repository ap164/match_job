import pytest
from transform import (
    normalize_location,
    work_mode_normalize,
    parse_experience_level,
    normalize_skills,
    parse_salary,
    normalize_contract_type,
    salary_option_vs_contract_type,
    normalize_full_contract_type,
    normalize_employment_type
)

from utils import fetch_exchange_rate

def test_normalize_location():
    assert normalize_location([]) == None
    assert normalize_location("") == None
    assert normalize_location(" Cała Polska (praca zdalna)Warszawa") == {"city": "Warszawa", "district": None}
    assert normalize_location(" Cała Polska (praca zdalna)Wrocław, Fabryczna") == {"city": "Wrocław", "district": "Fabryczna"}
    assert normalize_location("Warszawa") == {"city": "Warszawa","district": None,}
    assert normalize_location("Warszawa, Mokotów") == { "city": "Warszawa", "district": "Mokotów"}    
    assert normalize_location("Warszawa, Mokotów, Ursynów") == {"city": "Warszawa", "district": "Mokotów, Ursynów"}

def test_work_mode_normalize():
    assert work_mode_normalize([]) == None     
    assert work_mode_normalize([""]) == None
    assert work_mode_normalize(["Praca zdalna"]) == ["remote"]
    assert work_mode_normalize(["Praca hybrydowa"]) == ["hybrid"]
    assert work_mode_normalize(["Praca stacjonarna"]) == ["on-site"]
    assert work_mode_normalize(["Praca zdalna", "Praca hybrydowa"]) == ['remote', 'hybrid']
    assert work_mode_normalize(["Praca stacjonarna", "Praca zdalna"]) == ["on-site", "remote"]

def test_parse_experience_level():
    assert parse_experience_level([]) == None
    assert parse_experience_level([""]) == None
    assert parse_experience_level(["Junior"]) == ["junior"]
    assert parse_experience_level(["Mid"]) == ["mid"]
    assert parse_experience_level(["Senior"]) == ["senior"]
    assert parse_experience_level(["Junior", "Mid", "Senior"]) == ["junior", "mid", "senior"]
    assert parse_experience_level(["starszy specjalista (senior)"]) == ["senior"]
    assert parse_experience_level(["młodszy specjalista (junior)", "specjalista (mid / regular)"]) == ["junior", "mid"]
    assert parse_experience_level(["młodszy specjalista", "specjalista (mid / regular)"]) == ["junior", "mid"]
    assert parse_experience_level(["Junior", "Junior","Mid",]) == ["junior", "mid"]

def test_normalize_skills():
    assert normalize_skills([]) == None
    assert normalize_skills([""]) == None
    assert normalize_skills(["Python"]) == [{"skill":"python","level": "excpected"}]
    assert normalize_skills(["Python", "Python"]) == [{"skill":"python","level": "excpected"}]
    assert normalize_skills(["Python", "Java"]) == [{"skill":"python","level": "excpected"}, {"skill":"java","level": "excpected"}]
    assert normalize_skills(["SQL","PostgreSQL (optional)"]) == [{"skill":"sql","level": "excpected"}, {"skill":"postgresql","level": "optional"}]
    assert normalize_skills(["English (B2)","AWS (advanced)"]) == [{"skill":"english","level": "b2"}, {"skill":"aws","level": "advanced"}]

def test_parse_salary():
    assert parse_salary([]) == None
    assert parse_salary([""]) == None
    assert parse_salary(["18 000-22 000PLN/month (Net per month - B2B)"]) == [{"min": 112.50, 
                                                                               "max": 137.50, 
                                                                               "currency": "PLN", 
                                                                               "unit": "hour",
                                                                               "net_gross": "net",
                                                                                "contract": "b2b"}]

    assert parse_salary(["100–120zł netto (+VAT)/ godz"]) == [{"min": 100.00, 
                                                                               "max": 120.00, 
                                                                               "currency": "PLN", 
                                                                               "unit": "hour",
                                                                               "net_gross": "net",
                                                                                "contract": "b2b"}]

    assert parse_salary(["15 000-20 000PLN/month (Gross per month - Any)"]) == [{"min": 93.75, 
                                                                                "max": 125.00, 
                                                                                "currency": "PLN", 
                                                                                "unit": "hour",
                                                                                "net_gross": "gross",
                                                                                    "contract": "any"}]

    assert parse_salary(["8000–21000zł brutto/ mies."]) == [{"min": 50.00, 
                                                                                    "max": 131.25, 
                                                                                    "currency": "PLN", 
                                                                                    "unit": "hour",
                                                                                    "net_gross": "gross",
                                                                                    "contract": None}]
    
    assert parse_salary(["17 000-17 800PLN/month (Net per month - B2B)", "17 000-17 800PLN/month (Gross per month - Permanent)"]) == [
          {"min": 106.25, 
            "max": 111.25,
            "currency": "PLN",
            "unit": "hour",
            "net_gross": "net",
            "contract": "b2b"},
            {
            "min": 106.25,
            "max": 111.25,
            "currency": "PLN",
            "unit": "hour",
            "net_gross": "gross",
            "contract": "permanent"
            }]

    assert parse_salary([ "80–140zł/ godz. (zal. od umowy)"]) == [{"min": 80.00, 
                                                                                    "max": 140.00, 
                                                                                    "currency": "PLN", 
                                                                                    "unit": "hour",
                                                                                    "net_gross": None,
                                                                                    "contract": None}]
    assert parse_salary([ "170,00 zł netto (+ VAT) / godz."]) == [{"min": 170.00, 
                                                                                    "max": 170.00, 
                                                                                    "currency": "PLN", 
                                                                                    "unit": "hour",
                                                                                    "net_gross": "net",
                                                                                    "contract": "b2b"}]
    eur_rate = fetch_exchange_rate("EUR")
    result = parse_salary(["80–140€/ godz. (zal. od umowy)"])[0]
    assert result == {
        "min": pytest.approx(80 * eur_rate, abs=0.5),
        "max": pytest.approx(140 * eur_rate, abs=0.5),
        "currency": "PLN",
        "unit": "hour",
        "net_gross": None,
        "contract": None
    }
    

# def test_fetch_exchange_rate():
#     assert fetch_exchange_rate("EUR") == 4.2727 # Example value, actual value may vary 

def test_normalize_contract_type():
    assert normalize_contract_type("") == None
    assert normalize_contract_type(None) == None
    assert normalize_contract_type("b2b") == {"permanent": False, "b2b": True, "mandate": False}
    assert normalize_contract_type("business to business") == {"permanent": False, "b2b": True, "mandate": False}
    assert normalize_contract_type("umowa o pracę") == {"permanent": True, "b2b": False, "mandate": False}
    assert normalize_contract_type("employment contract") == {"permanent": True, "b2b": False, "mandate": False}
    assert normalize_contract_type("permanent") == {"permanent": True, "b2b": False, "mandate": False}
    assert normalize_contract_type("umowa o prace") == {"permanent": True, "b2b": False, "mandate": False}
    assert normalize_contract_type("umowa zlecenie") == {"permanent": False, "b2b": False, "mandate": True}
    assert normalize_contract_type("contract of mandate") == {"permanent": False, "b2b": False, "mandate": True}
    assert normalize_contract_type("any") == {"permanent": True, "b2b": True, "mandate": True}
    assert normalize_contract_type("****") == {"permanent": False, "b2b": False, "mandate": False}

def test_salary_option_vs_contract_type():
    base = {"permanent": False, "b2b": False, "mandate": False}
    salary = [{"contract": "b2b"}]
    assert salary_option_vs_contract_type(salary, base) == {"permanent": False, "b2b": True, "mandate": False}

    salary = [{"contract": "permanent"}]
    assert salary_option_vs_contract_type(salary, base) == {"permanent": True, "b2b": True, "mandate": False}

    salary = [{"contract": "any"}]
    assert salary_option_vs_contract_type(salary, base) == {"permanent": True, "b2b": True, "mandate": True}

    salary = [{"contract": "permanent"}, {"contract": "b2b"}]
    assert salary_option_vs_contract_type(salary, base.copy()) == {"permanent": True, "b2b": True, "mandate": False}

def test_normalize_full_contract_type():
    assert normalize_full_contract_type("", "") == None
    assert normalize_full_contract_type(None, None) == None    
    assert normalize_full_contract_type("b2b", None) == {"permanent": False, "b2b": True, "mandate": False}
    assert normalize_full_contract_type("Umowa o pracę", [{"contract": "b2b"}]) == {"permanent": True, "b2b": True, "mandate": False}
    assert normalize_full_contract_type("any", []) == {"permanent": True, "b2b": True, "mandate": True}
    assert normalize_full_contract_type("", [{"contract": "mandate"}]) == {"permanent": False, "b2b": False, "mandate": True}
    assert normalize_full_contract_type("b2b", [{"contract": "permanent"},{"contract": "b2b"}]) == {"permanent": True, "b2b": True, "mandate": False}
    assert normalize_full_contract_type(None, [{"contract": "permanent"},{"contract": "b2b"}]) == {"permanent": True, "b2b": True, "mandate": False}



def test_normalize_employment_type():
    assert normalize_employment_type("") == None
    assert normalize_employment_type(None) == None
    assert normalize_employment_type(12345) == None    
    assert normalize_employment_type("full-time") == {"full_time": True, "part_time": False}
    assert normalize_employment_type("Full–time") == {"full_time": True, "part_time": False}  # en dash
    assert normalize_employment_type("pełny etat") == {"full_time": True, "part_time": False}
    assert normalize_employment_type("pelny etat") == {"full_time": True, "part_time": False}
    assert normalize_employment_type("FULL TIME") == {"full_time": True, "part_time": False}
    assert normalize_employment_type("part-time") == {"full_time": False, "part_time": True}
    assert normalize_employment_type("Part–time") == {"full_time": False, "part_time": True}
    assert normalize_employment_type("czesc etatu") == {"full_time": False, "part_time": True}
    assert normalize_employment_type("część etatu") == {"full_time": False, "part_time": True}
    assert normalize_employment_type("dodatkowa") == {"full_time": False, "part_time": True}
    assert normalize_employment_type("tymczasowa") == {"full_time": False, "part_time": True}
    assert normalize_employment_type("pełny etat, dodatkowa") == {"full_time": True, "part_time": True}
    assert normalize_employment_type("FULL-TIME, CZĘŚĆ ETATU") == {"full_time": True, "part_time": True}
    assert normalize_employment_type("projekt") == {"full_time": False, "part_time": False, "other": "projekt"}
