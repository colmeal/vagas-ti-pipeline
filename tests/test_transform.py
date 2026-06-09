"""
tests/test_transform.py — Testes unitários das funções de transformação.
Cobre: parse_salary, classify_seniority, normalize_location, extract_stacks.
"""
import sys
sys.path.insert(0, "../etl")

import pytest
import pandas as pd

from transform import (
    parse_salary,
    classify_seniority,
    normalize_location,
    extract_stacks_from_title,
    safe_str,
    safe_float,
)


# -------------------------------------------------------------------
# parse_salary
# -------------------------------------------------------------------

class TestParseSalary:
    def test_range_usd(self):
        s_min, s_max = parse_salary("$80,000 - $120,000")
        assert s_min == 80000.0
        assert s_max == 120000.0

    def test_k_notation(self):
        s_min, s_max = parse_salary("80k - 120k")
        assert s_min == 80000.0
        assert s_max == 120000.0

    def test_single_value(self):
        s_min, s_max = parse_salary("$100,000")
        assert s_min == s_max == 100000.0

    def test_none_input(self):
        assert parse_salary(None) == (None, None)

    def test_empty_string(self):
        assert parse_salary("") == (None, None)

    def test_no_numbers(self):
        assert parse_salary("competitive salary") == (None, None)

    def test_up_to_pattern(self):
        s_min, s_max = parse_salary("up to $150,000")
        assert s_max == 150000.0


# -------------------------------------------------------------------
# classify_seniority
# -------------------------------------------------------------------

class TestClassifySeniority:
    def test_senior_in_title(self):
        assert classify_seniority("Senior Python Developer") == "Senior"

    def test_junior_in_title(self):
        assert classify_seniority("Junior Software Engineer") == "Junior"

    def test_staff_in_title(self):
        assert classify_seniority("Staff Engineer, ML") == "Staff"

    def test_level_overrides_title(self):
        # job_level Associate deve retornar Junior
        assert classify_seniority("Senior Developer", level="Associate") == "Junior"

    def test_none_title(self):
        result = classify_seniority(None)
        assert result == "Not Specified"

    def test_default_midlevel(self):
        assert classify_seniority("Software Engineer") == "Mid-Level"

    def test_lead_is_senior(self):
        assert classify_seniority("Lead Data Engineer") == "Senior"


# -------------------------------------------------------------------
# normalize_location
# -------------------------------------------------------------------

class TestNormalizeLocation:
    def test_onsite_default(self):
        loc = normalize_location("New York, NY", "United States")
        assert loc["modalidade"] == "Onsite"
        assert loc["pais"] == "United States"

    def test_remote_keyword(self):
        loc = normalize_location("Remote - Worldwide")
        assert loc["modalidade"] == "Remote"

    def test_hybrid_keyword(self):
        loc = normalize_location("Hybrid - London")
        assert loc["modalidade"] == "Hybrid"

    def test_none_location(self):
        loc = normalize_location(None, "Brazil")
        assert loc["pais"] == "Brazil"
        assert loc["regiao"] == "Unknown"


# -------------------------------------------------------------------
# extract_stacks_from_title
# -------------------------------------------------------------------

class TestExtractStacks:
    def test_python_detected(self):
        stacks = extract_stacks_from_title("Senior Python Developer")
        assert "python" in stacks

    def test_multiple_stacks(self):
        stacks = extract_stacks_from_title("Data Engineer — Python, Spark, AWS")
        assert "python" in stacks
        assert "spark"  in stacks
        assert "aws"    in stacks

    def test_no_stacks(self):
        stacks = extract_stacks_from_title("Office Manager")
        assert stacks == []

    def test_none_title(self):
        assert extract_stacks_from_title(None) == []


# -------------------------------------------------------------------
# Helpers safe_str / safe_float
# -------------------------------------------------------------------

class TestHelpers:
    def test_safe_str_normal(self):
        assert safe_str("  hello  ") == "hello"

    def test_safe_str_none(self):
        assert safe_str(None) is None

    def test_safe_str_empty(self):
        assert safe_str("   ") is None

    def test_safe_float_normal(self):
        assert safe_float("123.45") == 123.45

    def test_safe_float_with_dollar(self):
        assert safe_float("$1,500.00") == 1500.0

    def test_safe_float_none(self):
        assert safe_float(None) is None

    def test_safe_float_invalid(self):
        assert safe_float("abc") is None
