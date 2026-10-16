import pytest
from app.extractors.content.psgc_gazetteer import (
    PHILIPPINE_REGIONS,
    PHILIPPINE_PROVINCES,
    CORE_LGUS,
    COMMERCIAL_HUBS,
    lookup_location,
    infer_province_and_region,
    is_philippine_province,
    get_gazetteer,
    build_psgc_dataset,
    load_psgc_data
)
from app.extractors.content.location_extractor import (
    parse_philippine_address,
    extract_applicant_address,
    extract_inline_location,
    extract_location
)
from app.extractors.content.content_extractor import extract_content


def test_gazetteer_dataset_and_hierarchy():
    # 1. Check all 17 regions are present
    assert len(PHILIPPINE_REGIONS) == 17
    assert "NCR" in PHILIPPINE_REGIONS
    assert "Region IV-A" in PHILIPPINE_REGIONS
    assert "BARMM" in PHILIPPINE_REGIONS

    # 2. Check all 82 provinces + Metro Manila are present
    assert len(PHILIPPINE_PROVINCES) >= 83
    assert is_philippine_province("Rizal")
    assert is_philippine_province("Batangas")
    assert is_philippine_province("Cavite")
    assert is_philippine_province("Cebu")
    assert is_philippine_province("Davao del Sur")

    # 3. Check lookup and aliases
    qc = lookup_location("QC")
    assert qc is not None
    assert qc["canonical"] == "Quezon City"
    assert qc["province"] == "Metro Manila"

    dasma = lookup_location("Dasma")
    assert dasma is not None
    assert dasma["canonical"] == "Dasmariñas City"
    assert dasma["province"] == "Cavite"

    cdo = lookup_location("CDO")
    assert cdo is not None
    assert cdo["canonical"] == "Cagayan de Oro City"
    assert cdo["province"] == "Misamis Oriental"

    # 4. Check inference
    prov, reg = infer_province_and_region("Antipolo")
    assert prov == "Rizal"
    assert reg == "Region IV-A (CALABARZON)"

    prov2, reg2 = infer_province_and_region("Mandaue")
    assert prov2 == "Cebu"
    assert reg2 == "Region VII"


def test_pattern_1_suburban_subdivision():
    text = "Address: Blk 8 Lot 15 Phase 2, Carissa Homes East, Brgy. Bagumbayan, Teresa, Rizal 1880"
    res = extract_applicant_address(text)

    assert res["city_or_municipality"] == "Teresa"
    assert res["province"] == "Rizal"
    assert res["region"] == "Region IV-A (CALABARZON)"
    assert res["barangay"] == "Bagumbayan"
    assert res["zip_code"] == "1880"
    assert res["location_type"] == "Municipality"
    assert res["house_street_subdivision"] == "Blk 8 Lot 15 Phase 2, Carissa Homes East"
    assert res["normalized_location"] == "Teresa, Rizal"
    assert res["confidence_score"] >= 0.90


def test_pattern_2_provincial_purok_sitio():
    text = "Permanent Address: Purok 4, Sitio Maligaya, Brgy. San Roque, Sto. Tomas, Batangas"
    res = extract_applicant_address(text)

    assert res["city_or_municipality"] == "Santo Tomas City"
    assert res["province"] == "Batangas"
    assert res["region"] == "Region IV-A (CALABARZON)"
    assert res["barangay"] == "San Roque"
    assert res["house_street_subdivision"] == "Purok 4, Sitio Maligaya"
    assert res["location_type"] == "Component City"
    assert res["normalized_location"] == "Santo Tomas City, Batangas"
    assert res["confidence_score"] >= 0.90


def test_pattern_3_metro_manila_urban_street():
    text = "24-B Mabini St., Brgy. Kapitolyo, Pasig City, Metro Manila"
    res = extract_applicant_address(text)

    assert res["city_or_municipality"] == "Pasig City"
    assert res["province"] == "Metro Manila"
    assert res["region"] == "NCR"
    assert res["barangay"] == "Kapitolyo"
    assert res["house_street_subdivision"] == "24-B Mabini St."
    assert res["location_type"] == "HUC"
    assert res["normalized_location"] == "Pasig City, Metro Manila"
    assert res["confidence_score"] >= 0.90


def test_pattern_4_work_experience_commercial_hubs_and_branches():
    # 4a. Fast food employer branch
    snip1 = "Jollibee Foods Corporation - Crossing Branch, Calamba, Laguna"
    res1 = extract_inline_location(snip1)
    assert res1["city_or_municipality"] == "Calamba City"
    assert res1["province"] == "Laguna"
    assert res1["region"] == "Region IV-A (CALABARZON)"
    assert res1["business_district_or_branch"] == "Crossing Branch"
    assert res1["normalized_location"] == "Calamba City, Laguna"

    # 4b. Corporate BPO Central Business District (BGC)
    snip2 = "Accenture Philippines | BGC, Taguig City"
    res2 = extract_inline_location(snip2)
    assert res2["city_or_municipality"] == "Taguig City"
    assert res2["province"] == "Metro Manila"
    assert res2["region"] == "NCR"
    assert res2["business_district_or_branch"] == "BGC"
    assert res2["normalized_location"] == "Taguig City, Metro Manila"

    # 4c. Mall branch
    snip3 = "Chowking - SM City Taytay, Rizal"
    res3 = extract_inline_location(snip3)
    assert res3["city_or_municipality"] == "Taytay"
    assert res3["province"] == "Rizal"
    assert res3["region"] == "Region IV-A (CALABARZON)"
    assert res3["business_district_or_branch"] == "SM City Taytay"
    assert res3["normalized_location"] == "Taytay, Rizal"


def test_pattern_5_municipality_inference_and_disambiguation():
    # 5a. Campus inference
    snip1 = "ICCT Colleges - Cainta Main Campus"
    res1 = extract_inline_location(snip1)
    assert res1["city_or_municipality"] == "Cainta"
    assert res1["province"] == "Rizal"
    assert res1["region"] == "Region IV-A (CALABARZON)"
    assert res1["business_district_or_branch"] == "Cainta Main Campus"
    assert res1["normalized_location"] == "Cainta, Rizal"

    # 5b. School name false-positive avoidance
    snip2 = "Rizal National Science High School, Binangonan, Rizal"
    res2 = extract_inline_location(snip2)
    assert res2["city_or_municipality"] == "Binangonan"
    assert res2["province"] == "Rizal"
    assert res2["region"] == "Region IV-A (CALABARZON)"
    assert res2["normalized_location"] == "Binangonan, Rizal"


def test_backward_compatibility_extract_location():
    text1 = "Address: Blk 8 Lot 15 Phase 2, Carissa Homes East, Brgy. Bagumbayan, Teresa, Rizal 1880"
    assert extract_location(text1) == "Teresa, Rizal"

    text2 = "MARVIN FABRICANTE\n09171234567 | marvin@gmail.com | 24-B Mabini St., Brgy. Kapitolyo, Pasig City, Metro Manila"
    assert extract_location(text2) == "Pasig City, Metro Manila"

    text3 = "JUAN DELA CRUZ\nCainta, Rizal\n09181234567"
    assert extract_location(text3) == "Cainta, Rizal"


def test_psgc_json_builder_and_cache(tmp_path):
    cache_file = tmp_path / "psgc_test_locations.json"
    target = build_psgc_dataset(str(cache_file))
    assert cache_file.exists()

    loaded = load_psgc_data(str(cache_file))
    assert "regions" in loaded
    assert "provinces" in loaded
    assert "lgus" in loaded
    assert "hubs" in loaded


def test_content_extractor_integration():
    resume_text = """
MARVIN FABRICANTE
Senior Software Engineer
09171234567 | marvin@gmail.com | Blk 8 Lot 15 Phase 2, Carissa Homes East, Brgy. Bagumbayan, Teresa, Rizal 1880

PROFESSIONAL EXPERIENCE
Senior Full Stack Developer
Accenture Philippines | BGC, Taguig City
2023 - Present
"""
    extracted = extract_content(resume_text)
    assert "location" in extracted
    assert extracted["location"] == "Teresa, Rizal"
    assert "location_details" in extracted
    assert extracted["location_details"]["city_or_municipality"] == "Teresa"
    assert extracted["location_details"]["province"] == "Rizal"
    assert extracted["location_details"]["zip_code"] == "1880"
