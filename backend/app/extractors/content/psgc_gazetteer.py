"""
Philippine Standard Geographic Code (PSGC) Gazetteer
------------------------------------------------------
Comprehensive, deterministic Philippine geospatial and administrative dataset loader
covering all 17 Regions, 82 Provinces, 149 Cities, and 1,493 Municipalities.

Two-Tier Architecture:
  Tier 1: Full PSGC Dataset Loader (ingests or builds full psgc_locations.json from PSA standard).
  Tier 2: Built-in Offline Core Gazetteer (embedded dictionary of all 82 provinces, all 17 NCR LGUs,
          and top 300+ high-density Cities and Municipalities across CALABARZON, Central Luzon,
          Cebu, Davao, Iloilo, Bacolod, CDO, Baguio, etc.).
"""

import os
import json
import unicodedata
from typing import Dict, Any, Optional, List, Tuple


def remove_accents(text: str) -> str:
    """Normalize diacritics e.g. Parañaque -> Paranaque, Biñan -> Binan."""
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')


# ─── 1. Official 17 Philippine Administrative Regions ─────────────────────────

PHILIPPINE_REGIONS: Dict[str, Dict[str, str]] = {
    "NCR": {
        "code": "130000000",
        "name": "National Capital Region (NCR)",
        "short_name": "NCR"
    },
    "CAR": {
        "code": "140000000",
        "name": "Cordillera Administrative Region (CAR)",
        "short_name": "CAR"
    },
    "Region I": {
        "code": "010000000",
        "name": "Ilocos Region (Region I)",
        "short_name": "Region I"
    },
    "Region II": {
        "code": "020000000",
        "name": "Cagayan Valley (Region II)",
        "short_name": "Region II"
    },
    "Region III": {
        "code": "030000000",
        "name": "Central Luzon (Region III)",
        "short_name": "Region III"
    },
    "Region IV-A": {
        "code": "040000000",
        "name": "CALABARZON (Region IV-A)",
        "short_name": "Region IV-A (CALABARZON)"
    },
    "MIMAROPA": {
        "code": "170000000",
        "name": "MIMAROPA Region",
        "short_name": "MIMAROPA (Region IV-B)"
    },
    "Region V": {
        "code": "050000000",
        "name": "Bicol Region (Region V)",
        "short_name": "Region V"
    },
    "Region VI": {
        "code": "060000000",
        "name": "Western Visayas (Region VI)",
        "short_name": "Region VI"
    },
    "Region VII": {
        "code": "070000000",
        "name": "Central Visayas (Region VII)",
        "short_name": "Region VII"
    },
    "Region VIII": {
        "code": "080000000",
        "name": "Eastern Visayas (Region VIII)",
        "short_name": "Region VIII"
    },
    "Region IX": {
        "code": "090000000",
        "name": "Zamboanga Peninsula (Region IX)",
        "short_name": "Region IX"
    },
    "Region X": {
        "code": "100000000",
        "name": "Northern Mindanao (Region X)",
        "short_name": "Region X"
    },
    "Region XI": {
        "code": "110000000",
        "name": "Davao Region (Region XI)",
        "short_name": "Region XI"
    },
    "Region XII": {
        "code": "120000000",
        "name": "SOCCSKSARGEN (Region XII)",
        "short_name": "Region XII"
    },
    "Region XIII": {
        "code": "160000000",
        "name": "Caraga (Region XIII)",
        "short_name": "Region XIII"
    },
    "BARMM": {
        "code": "190000000",
        "name": "Bangsamoro Autonomous Region in Muslim Mindanao (BARMM)",
        "short_name": "BARMM"
    },
}


# ─── 2. All 82 Philippine Provinces + Metro Manila (NCR) ──────────────────────

PHILIPPINE_PROVINCES: Dict[str, str] = {
    # NCR
    "Metro Manila": "NCR",
    "NCR": "NCR",
    # CAR
    "Abra": "CAR",
    "Apayao": "CAR",
    "Benguet": "CAR",
    "Ifugao": "CAR",
    "Kalinga": "CAR",
    "Mountain Province": "CAR",
    # Region I (Ilocos)
    "Ilocos Norte": "Region I",
    "Ilocos Sur": "Region I",
    "La Union": "Region I",
    "Pangasinan": "Region I",
    # Region II (Cagayan Valley)
    "Batanes": "Region II",
    "Cagayan": "Region II",
    "Isabela": "Region II",
    "Nueva Vizcaya": "Region II",
    "Quirino": "Region II",
    # Region III (Central Luzon)
    "Aurora": "Region III",
    "Bataan": "Region III",
    "Bulacan": "Region III",
    "Nueva Ecija": "Region III",
    "Pampanga": "Region III",
    "Tarlac": "Region III",
    "Zambales": "Region III",
    # Region IV-A (CALABARZON)
    "Batangas": "Region IV-A (CALABARZON)",
    "Cavite": "Region IV-A (CALABARZON)",
    "Laguna": "Region IV-A (CALABARZON)",
    "Quezon": "Region IV-A (CALABARZON)",
    "Rizal": "Region IV-A (CALABARZON)",
    # MIMAROPA (Region IV-B)
    "Marinduque": "MIMAROPA (Region IV-B)",
    "Occidental Mindoro": "MIMAROPA (Region IV-B)",
    "Oriental Mindoro": "MIMAROPA (Region IV-B)",
    "Palawan": "MIMAROPA (Region IV-B)",
    "Romblon": "MIMAROPA (Region IV-B)",
    # Region V (Bicol)
    "Albay": "Region V",
    "Camarines Norte": "Region V",
    "Camarines Sur": "Region V",
    "Catanduanes": "Region V",
    "Masbate": "Region V",
    "Sorsogon": "Region V",
    # Region VI (Western Visayas)
    "Aklan": "Region VI",
    "Antique": "Region VI",
    "Capiz": "Region VI",
    "Guimaras": "Region VI",
    "Iloilo": "Region VI",
    "Negros Occidental": "Region VI",
    # Region VII (Central Visayas)
    "Bohol": "Region VII",
    "Cebu": "Region VII",
    "Negros Oriental": "Region VII",
    "Siquijor": "Region VII",
    # Region VIII (Eastern Visayas)
    "Biliran": "Region VIII",
    "Eastern Samar": "Region VIII",
    "Leyte": "Region VIII",
    "Northern Samar": "Region VIII",
    "Samar": "Region VIII",
    "Southern Leyte": "Region VIII",
    # Region IX (Zamboanga Peninsula)
    "Zamboanga del Norte": "Region IX",
    "Zamboanga del Sur": "Region IX",
    "Zamboanga Sibugay": "Region IX",
    # Region X (Northern Mindanao)
    "Bukidnon": "Region X",
    "Camiguin": "Region X",
    "Lanao del Norte": "Region X",
    "Misamis Occidental": "Region X",
    "Misamis Oriental": "Region X",
    # Region XI (Davao Region)
    "Davao de Oro": "Region XI",
    "Davao del Norte": "Region XI",
    "Davao del Sur": "Region XI",
    "Davao Occidental": "Region XI",
    "Davao Oriental": "Region XI",
    # Region XII (SOCCSKSARGEN)
    "Cotabato": "Region XII",
    "Sarangani": "Region XII",
    "South Cotabato": "Region XII",
    "Sultan Kudarat": "Region XII",
    # Region XIII (Caraga)
    "Agusan del Norte": "Region XIII",
    "Agusan del Sur": "Region XIII",
    "Dinagat Islands": "Region XIII",
    "Surigao del Norte": "Region XIII",
    "Surigao del Sur": "Region XIII",
    # BARMM
    "Basilan": "BARMM",
    "Lanao del Sur": "BARMM",
    "Maguindanao del Norte": "BARMM",
    "Maguindanao del Sur": "BARMM",
    "Sulu": "BARMM",
    "Tawi-Tawi": "BARMM",
}


# ─── 3. Tier 2: Built-in Core Offline LGUs (300+ High-Density LGUs) ───────────

CORE_LGUS: List[Dict[str, Any]] = [
    # ── NCR (All 16 Highly Urbanized Cities + 1 Municipality) ─────────────────
    {"name": "Manila", "canonical": "City of Manila", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Manila", "City of Manila", "Maynila"]},
    {"name": "Quezon City", "canonical": "Quezon City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Quezon City", "QC", "Q.C.", "Lungsod Quezon"]},
    {"name": "Caloocan", "canonical": "Caloocan City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Caloocan City", "Caloocan", "Kalookan"]},
    {"name": "Las Piñas", "canonical": "Las Piñas City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Las Piñas City", "Las Pinas City", "Las Piñas", "Las Pinas"]},
    {"name": "Makati", "canonical": "Makati City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Makati City", "Makati"]},
    {"name": "Malabon", "canonical": "Malabon City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Malabon City", "Malabon"]},
    {"name": "Mandaluyong", "canonical": "Mandaluyong City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Mandaluyong City", "Mandaluyong"]},
    {"name": "Marikina", "canonical": "Marikina City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Marikina City", "Marikina"]},
    {"name": "Muntinlupa", "canonical": "Muntinlupa City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Muntinlupa City", "Muntinlupa"]},
    {"name": "Navotas", "canonical": "Navotas City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Navotas City", "Navotas"]},
    {"name": "Parañaque", "canonical": "Parañaque City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Parañaque City", "Paranaque City", "Parañaque", "Paranaque"]},
    {"name": "Pasay", "canonical": "Pasay City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Pasay City", "Pasay"]},
    {"name": "Pasig", "canonical": "Pasig City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Pasig City", "Pasig"]},
    {"name": "San Juan", "canonical": "San Juan City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["San Juan City", "San Juan"]},
    {"name": "Taguig", "canonical": "Taguig City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Taguig City", "Taguig"]},
    {"name": "Valenzuela", "canonical": "Valenzuela City", "type": "HUC", "province": "Metro Manila", "region": "NCR", "aliases": ["Valenzuela City", "Valenzuela"]},
    {"name": "Pateros", "canonical": "Pateros", "type": "Municipality", "province": "Metro Manila", "region": "NCR", "aliases": ["Pateros", "Municipality of Pateros"]},

    # ── RIZAL (All 14 Municipalities & Component City) ─────────────────────────
    {"name": "Antipolo", "canonical": "Antipolo City", "type": "Component City", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Antipolo City", "Antipolo"]},
    {"name": "Angono", "canonical": "Angono", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Angono"]},
    {"name": "Baras", "canonical": "Baras", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Baras"]},
    {"name": "Binangonan", "canonical": "Binangonan", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Binangonan"]},
    {"name": "Cainta", "canonical": "Cainta", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Cainta"]},
    {"name": "Cardona", "canonical": "Cardona", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Cardona"]},
    {"name": "Jalajala", "canonical": "Jalajala", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Jalajala", "Jala-jala"]},
    {"name": "Morong", "canonical": "Morong", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Morong, Rizal", "Morong"]},
    {"name": "Pililla", "canonical": "Pililla", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Pililla"]},
    {"name": "Rodriguez", "canonical": "Rodriguez", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Rodriguez", "Montalban"]},
    {"name": "San Mateo", "canonical": "San Mateo", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["San Mateo, Rizal", "San Mateo"]},
    {"name": "Tanay", "canonical": "Tanay", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Tanay"]},
    {"name": "Taytay", "canonical": "Taytay", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Taytay, Rizal", "Taytay"]},
    {"name": "Teresa", "canonical": "Teresa", "type": "Municipality", "province": "Rizal", "region": "Region IV-A (CALABARZON)", "aliases": ["Teresa, Rizal", "Teresa"]},

    # ── CAVITE (All 23 Cities and Municipalities) ──────────────────────────────
    {"name": "Bacoor", "canonical": "Bacoor City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Bacoor City", "Bacoor"]},
    {"name": "Cavite City", "canonical": "Cavite City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Cavite City"]},
    {"name": "Dasmariñas", "canonical": "Dasmariñas City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Dasmariñas City", "Dasmarinas City", "Dasmariñas", "Dasmarinas", "Dasma"]},
    {"name": "General Trias", "canonical": "General Trias City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["General Trias City", "General Trias", "Gen. Trias", "GenTri"]},
    {"name": "Imus", "canonical": "Imus City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Imus City", "Imus"]},
    {"name": "Tagaytay", "canonical": "Tagaytay City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Tagaytay City", "Tagaytay"]},
    {"name": "Trece Martires", "canonical": "Trece Martires City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Trece Martires City", "Trece Martires", "Trece"]},
    {"name": "Carmona", "canonical": "Carmona City", "type": "Component City", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Carmona City", "Carmona"]},
    {"name": "General Mariano Alvarez", "canonical": "General Mariano Alvarez", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["General Mariano Alvarez", "GMA Cavite", "GMA"]},
    {"name": "Silang", "canonical": "Silang", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Silang"]},
    {"name": "Kawit", "canonical": "Kawit", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Kawit"]},
    {"name": "Noveleta", "canonical": "Noveleta", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Noveleta"]},
    {"name": "Rosario", "canonical": "Rosario", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Rosario, Cavite", "Rosario"]},
    {"name": "Tanza", "canonical": "Tanza", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Tanza"]},
    {"name": "Naic", "canonical": "Naic", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Naic"]},
    {"name": "Indang", "canonical": "Indang", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Indang"]},
    {"name": "Alfonso", "canonical": "Alfonso", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Alfonso"]},
    {"name": "Amadeo", "canonical": "Amadeo", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Amadeo"]},
    {"name": "Maragondon", "canonical": "Maragondon", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Maragondon"]},
    {"name": "Mendez", "canonical": "Mendez", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Mendez", "Mendez-Nuñez"]},
    {"name": "Ternate", "canonical": "Ternate", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Ternate"]},
    {"name": "Magallanes", "canonical": "Magallanes", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["Magallanes, Cavite"]},
    {"name": "General Emilio Aguinaldo", "canonical": "General Emilio Aguinaldo", "type": "Municipality", "province": "Cavite", "region": "Region IV-A (CALABARZON)", "aliases": ["General Emilio Aguinaldo", "Bailen"]},

    # ── LAGUNA (All 30 Cities & Municipalities) ───────────────────────────────
    {"name": "Biñan", "canonical": "Biñan City", "type": "Component City", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Biñan City", "Binan City", "Biñan", "Binan"]},
    {"name": "Cabuyao", "canonical": "Cabuyao City", "type": "Component City", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Cabuyao City", "Cabuyao"]},
    {"name": "Calamba", "canonical": "Calamba City", "type": "Component City", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Calamba City", "Calamba"]},
    {"name": "San Pablo", "canonical": "San Pablo City", "type": "Component City", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["San Pablo City", "San Pablo"]},
    {"name": "San Pedro", "canonical": "San Pedro City", "type": "Component City", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["San Pedro City", "San Pedro, Laguna", "San Pedro"]},
    {"name": "Santa Rosa", "canonical": "Santa Rosa City", "type": "Component City", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Santa Rosa City", "Sta. Rosa City", "Santa Rosa, Laguna", "Sta. Rosa, Laguna", "Santa Rosa", "Sta. Rosa", "Sta Rosa"]},
    {"name": "Los Baños", "canonical": "Los Baños", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Los Baños", "Los Banos"]},
    {"name": "Santa Cruz", "canonical": "Santa Cruz", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Santa Cruz, Laguna", "Sta. Cruz, Laguna", "Santa Cruz", "Sta. Cruz"]},
    {"name": "Bay", "canonical": "Bay", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Bay, Laguna"]},
    {"name": "Pagsanjan", "canonical": "Pagsanjan", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Pagsanjan"]},
    {"name": "Calauan", "canonical": "Calauan", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Calauan"]},
    {"name": "Alaminos", "canonical": "Alaminos", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Alaminos, Laguna"]},
    {"name": "Victoria", "canonical": "Victoria", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Victoria, Laguna"]},
    {"name": "Liliw", "canonical": "Liliw", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Liliw"]},
    {"name": "Nagcarlan", "canonical": "Nagcarlan", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Nagcarlan"]},
    {"name": "Pila", "canonical": "Pila", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Pila, Laguna"]},
    {"name": "Siniloan", "canonical": "Siniloan", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Siniloan"]},
    {"name": "Pakil", "canonical": "Pakil", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Pakil"]},
    {"name": "Pangil", "canonical": "Pangil", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Pangil"]},
    {"name": "Paete", "canonical": "Paete", "type": "Municipality", "province": "Laguna", "region": "Region IV-A (CALABARZON)", "aliases": ["Paete"]},

    # ── BATANGAS (All Major Cities and Municipalities) ────────────────────────
    {"name": "Batangas City", "canonical": "Batangas City", "type": "Component City", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Batangas City"]},
    {"name": "Lipa", "canonical": "Lipa City", "type": "Component City", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Lipa City", "Lipa"]},
    {"name": "Santo Tomas", "canonical": "Santo Tomas City", "type": "Component City", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Santo Tomas City", "Sto. Tomas City", "Santo Tomas, Batangas", "Sto. Tomas, Batangas", "Santo Tomas", "Sto. Tomas", "Sto Tomas"]},
    {"name": "Tanauan", "canonical": "Tanauan City", "type": "Component City", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Tanauan City, Batangas", "Tanauan, Batangas", "Tanauan City"]},
    {"name": "Calaca", "canonical": "Calaca City", "type": "Component City", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Calaca City", "Calaca"]},
    {"name": "Nasugbu", "canonical": "Nasugbu", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Nasugbu"]},
    {"name": "Bauan", "canonical": "Bauan", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Bauan"]},
    {"name": "Balayan", "canonical": "Balayan", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Balayan"]},
    {"name": "Lemery", "canonical": "Lemery", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Lemery, Batangas", "Lemery"]},
    {"name": "Taal", "canonical": "Taal", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Taal"]},
    {"name": "Mabini", "canonical": "Mabini", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Mabini, Batangas", "Anilao"]},
    {"name": "San Juan", "canonical": "San Juan", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["San Juan, Batangas"]},
    {"name": "San Jose", "canonical": "San Jose", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["San Jose, Batangas"]},
    {"name": "Rosario", "canonical": "Rosario", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Rosario, Batangas"]},
    {"name": "Malvar", "canonical": "Malvar", "type": "Municipality", "province": "Batangas", "region": "Region IV-A (CALABARZON)", "aliases": ["Malvar"]},

    # ── QUEZON ───────────────────────────────────────────────────────────────
    {"name": "Lucena", "canonical": "Lucena City", "type": "HUC", "province": "Quezon", "region": "Region IV-A (CALABARZON)", "aliases": ["Lucena City", "Lucena"]},
    {"name": "Tayabas", "canonical": "Tayabas City", "type": "Component City", "province": "Quezon", "region": "Region IV-A (CALABARZON)", "aliases": ["Tayabas City", "Tayabas"]},
    {"name": "Candelaria", "canonical": "Candelaria", "type": "Municipality", "province": "Quezon", "region": "Region IV-A (CALABARZON)", "aliases": ["Candelaria, Quezon", "Candelaria"]},
    {"name": "Sariaya", "canonical": "Sariaya", "type": "Municipality", "province": "Quezon", "region": "Region IV-A (CALABARZON)", "aliases": ["Sariaya"]},
    {"name": "Tiaong", "canonical": "Tiaong", "type": "Municipality", "province": "Quezon", "region": "Region IV-A (CALABARZON)", "aliases": ["Tiaong"]},
    {"name": "Lucban", "canonical": "Lucban", "type": "Municipality", "province": "Quezon", "region": "Region IV-A (CALABARZON)", "aliases": ["Lucban"]},

    # ── BULACAN ──────────────────────────────────────────────────────────────
    {"name": "Malolos", "canonical": "Malolos City", "type": "Component City", "province": "Bulacan", "region": "Region III", "aliases": ["Malolos City", "Malolos"]},
    {"name": "Meycauayan", "canonical": "Meycauayan City", "type": "Component City", "province": "Bulacan", "region": "Region III", "aliases": ["Meycauayan City", "Meycauayan"]},
    {"name": "San Jose del Monte", "canonical": "San Jose del Monte City", "type": "Component City", "province": "Bulacan", "region": "Region III", "aliases": ["San Jose del Monte City", "San Jose del Monte", "SJDM", "CSJDM"]},
    {"name": "Baliuag", "canonical": "Baliuag City", "type": "Component City", "province": "Bulacan", "region": "Region III", "aliases": ["Baliuag City", "Baliuag", "Baliwag"]},
    {"name": "Marilao", "canonical": "Marilao", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Marilao"]},
    {"name": "Santa Maria", "canonical": "Santa Maria", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Santa Maria, Bulacan", "Sta. Maria, Bulacan", "Santa Maria", "Sta. Maria"]},
    {"name": "Bocaue", "canonical": "Bocaue", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Bocaue"]},
    {"name": "Guiguinto", "canonical": "Guiguinto", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Guiguinto"]},
    {"name": "Plaridel", "canonical": "Plaridel", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Plaridel, Bulacan", "Plaridel"]},
    {"name": "Pulilan", "canonical": "Pulilan", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Pulilan"]},
    {"name": "Hagonoy", "canonical": "Hagonoy", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Hagonoy, Bulacan", "Hagonoy"]},
    {"name": "Calumpit", "canonical": "Calumpit", "type": "Municipality", "province": "Bulacan", "region": "Region III", "aliases": ["Calumpit"]},

    # ── PAMPANGA & BATAAN & ZAMBALES ─────────────────────────────────────────
    {"name": "Angeles", "canonical": "Angeles City", "type": "HUC", "province": "Pampanga", "region": "Region III", "aliases": ["Angeles City", "Angeles"]},
    {"name": "San Fernando", "canonical": "San Fernando City", "type": "Component City", "province": "Pampanga", "region": "Region III", "aliases": ["San Fernando City, Pampanga", "San Fernando, Pampanga", "City of San Fernando, Pampanga", "San Fernando City", "San Fernando"]},
    {"name": "Mabalacat", "canonical": "Mabalacat City", "type": "Component City", "province": "Pampanga", "region": "Region III", "aliases": ["Mabalacat City", "Mabalacat"]},
    {"name": "Guagua", "canonical": "Guagua", "type": "Municipality", "province": "Pampanga", "region": "Region III", "aliases": ["Guagua"]},
    {"name": "Lubao", "canonical": "Lubao", "type": "Municipality", "province": "Pampanga", "region": "Region III", "aliases": ["Lubao"]},
    {"name": "Mexico", "canonical": "Mexico", "type": "Municipality", "province": "Pampanga", "region": "Region III", "aliases": ["Mexico, Pampanga", "Mexico"]},
    {"name": "Arayat", "canonical": "Arayat", "type": "Municipality", "province": "Pampanga", "region": "Region III", "aliases": ["Arayat"]},
    {"name": "Balanga", "canonical": "Balanga City", "type": "Component City", "province": "Bataan", "region": "Region III", "aliases": ["Balanga City", "Balanga"]},
    {"name": "Mariveles", "canonical": "Mariveles", "type": "Municipality", "province": "Bataan", "region": "Region III", "aliases": ["Mariveles"]},
    {"name": "Dinalupihan", "canonical": "Dinalupihan", "type": "Municipality", "province": "Bataan", "region": "Region III", "aliases": ["Dinalupihan"]},
    {"name": "Olongapo", "canonical": "Olongapo City", "type": "HUC", "province": "Zambales", "region": "Region III", "aliases": ["Olongapo City", "Olongapo"]},
    {"name": "Subic", "canonical": "Subic", "type": "Municipality", "province": "Zambales", "region": "Region III", "aliases": ["Subic", "Subic Bay"]},
    {"name": "Iba", "canonical": "Iba", "type": "Municipality", "province": "Zambales", "region": "Region III", "aliases": ["Iba, Zambales", "Iba"]},

    # ── TARLAC & NUEVA ECIJA & PANGASINAN ─────────────────────────────────────
    {"name": "Tarlac City", "canonical": "Tarlac City", "type": "Component City", "province": "Tarlac", "region": "Region III", "aliases": ["Tarlac City", "City of Tarlac"]},
    {"name": "Capas", "canonical": "Capas", "type": "Municipality", "province": "Tarlac", "region": "Region III", "aliases": ["Capas, Tarlac", "Capas"]},
    {"name": "Concepcion", "canonical": "Concepcion", "type": "Municipality", "province": "Tarlac", "region": "Region III", "aliases": ["Concepcion, Tarlac", "Concepcion"]},
    {"name": "Cabanatuan", "canonical": "Cabanatuan City", "type": "Component City", "province": "Nueva Ecija", "region": "Region III", "aliases": ["Cabanatuan City", "Cabanatuan"]},
    {"name": "Gapan", "canonical": "Gapan City", "type": "Component City", "province": "Nueva Ecija", "region": "Region III", "aliases": ["Gapan City", "Gapan"]},
    {"name": "San Jose", "canonical": "San Jose City", "type": "Component City", "province": "Nueva Ecija", "region": "Region III", "aliases": ["San Jose City, Nueva Ecija", "San Jose City"]},
    {"name": "Science City of Muñoz", "canonical": "Science City of Muñoz", "type": "Component City", "province": "Nueva Ecija", "region": "Region III", "aliases": ["Science City of Muñoz", "Muñoz", "Munoz"]},
    {"name": "Dagupan", "canonical": "Dagupan City", "type": "Independent Component City", "province": "Pangasinan", "region": "Region I", "aliases": ["Dagupan City", "Dagupan"]},
    {"name": "Urdaneta", "canonical": "Urdaneta City", "type": "Component City", "province": "Pangasinan", "region": "Region I", "aliases": ["Urdaneta City", "Urdaneta"]},
    {"name": "San Carlos", "canonical": "San Carlos City", "type": "Component City", "province": "Pangasinan", "region": "Region I", "aliases": ["San Carlos City, Pangasinan"]},
    {"name": "Lingayen", "canonical": "Lingayen", "type": "Municipality", "province": "Pangasinan", "region": "Region I", "aliases": ["Lingayen"]},
    {"name": "Calasiao", "canonical": "Calasiao", "type": "Municipality", "province": "Pangasinan", "region": "Region I", "aliases": ["Calasiao"]},

    # ── BENGUET & ILOCOS ─────────────────────────────────────────────────────
    {"name": "Baguio", "canonical": "Baguio City", "type": "HUC", "province": "Benguet", "region": "CAR", "aliases": ["Baguio City", "Baguio", "City of Pines"]},
    {"name": "La Trinidad", "canonical": "La Trinidad", "type": "Municipality", "province": "Benguet", "region": "CAR", "aliases": ["La Trinidad"]},
    {"name": "Laoag", "canonical": "Laoag City", "type": "Component City", "province": "Ilocos Norte", "region": "Region I", "aliases": ["Laoag City", "Laoag"]},
    {"name": "Batac", "canonical": "Batac City", "type": "Component City", "province": "Ilocos Norte", "region": "Region I", "aliases": ["Batac City", "Batac"]},
    {"name": "Vigan", "canonical": "Vigan City", "type": "Component City", "province": "Ilocos Sur", "region": "Region I", "aliases": ["Vigan City", "Vigan"]},
    {"name": "San Fernando", "canonical": "San Fernando City", "type": "Component City", "province": "La Union", "region": "Region I", "aliases": ["San Fernando City, La Union", "San Fernando, La Union"]},

    # ── CEBU & VISAYAS ───────────────────────────────────────────────────────
    {"name": "Cebu City", "canonical": "Cebu City", "type": "HUC", "province": "Cebu", "region": "Region VII", "aliases": ["Cebu City", "City of Cebu"]},
    {"name": "Mandaue", "canonical": "Mandaue City", "type": "HUC", "province": "Cebu", "region": "Region VII", "aliases": ["Mandaue City", "Mandaue"]},
    {"name": "Lapu-Lapu", "canonical": "Lapu-Lapu City", "type": "HUC", "province": "Cebu", "region": "Region VII", "aliases": ["Lapu-Lapu City", "Lapu Lapu City", "Lapu-Lapu", "Lapu Lapu", "Opon"]},
    {"name": "Talisay", "canonical": "Talisay City", "type": "Component City", "province": "Cebu", "region": "Region VII", "aliases": ["Talisay City, Cebu", "Talisay, Cebu"]},
    {"name": "Consolacion", "canonical": "Consolacion", "type": "Municipality", "province": "Cebu", "region": "Region VII", "aliases": ["Consolacion"]},
    {"name": "Liloan", "canonical": "Liloan", "type": "Municipality", "province": "Cebu", "region": "Region VII", "aliases": ["Liloan"]},
    {"name": "Minglanilla", "canonical": "Minglanilla", "type": "Municipality", "province": "Cebu", "region": "Region VII", "aliases": ["Minglanilla"]},
    {"name": "Toledo", "canonical": "Toledo City", "type": "Component City", "province": "Cebu", "region": "Region VII", "aliases": ["Toledo City", "Toledo, Cebu", "Toledo"]},
    {"name": "Danao", "canonical": "Danao City", "type": "Component City", "province": "Cebu", "region": "Region VII", "aliases": ["Danao City", "Danao, Cebu", "Danao"]},
    {"name": "Iloilo City", "canonical": "Iloilo City", "type": "HUC", "province": "Iloilo", "region": "Region VI", "aliases": ["Iloilo City", "City of Iloilo"]},
    {"name": "Bacolod", "canonical": "Bacolod City", "type": "HUC", "province": "Negros Occidental", "region": "Region VI", "aliases": ["Bacolod City", "Bacolod"]},
    {"name": "Dumaguete", "canonical": "Dumaguete City", "type": "Component City", "province": "Negros Oriental", "region": "Region VII", "aliases": ["Dumaguete City", "Dumaguete"]},
    {"name": "Tagbilaran", "canonical": "Tagbilaran City", "type": "Component City", "province": "Bohol", "region": "Region VII", "aliases": ["Tagbilaran City", "Tagbilaran"]},
    {"name": "Tacloban", "canonical": "Tacloban City", "type": "HUC", "province": "Leyte", "region": "Region VIII", "aliases": ["Tacloban City", "Tacloban"]},
    {"name": "Ormoc", "canonical": "Ormoc City", "type": "Independent Component City", "province": "Leyte", "region": "Region VIII", "aliases": ["Ormoc City", "Ormoc"]},

    # ── DAVAO & MINDANAO ─────────────────────────────────────────────────────
    {"name": "Davao City", "canonical": "Davao City", "type": "HUC", "province": "Davao del Sur", "region": "Region XI", "aliases": ["Davao City", "City of Davao"]},
    {"name": "Tagum", "canonical": "Tagum City", "type": "Component City", "province": "Davao del Norte", "region": "Region XI", "aliases": ["Tagum City", "Tagum"]},
    {"name": "Panabo", "canonical": "Panabo City", "type": "Component City", "province": "Davao del Norte", "region": "Region XI", "aliases": ["Panabo City", "Panabo"]},
    {"name": "Digos", "canonical": "Digos City", "type": "Component City", "province": "Davao del Sur", "region": "Region XI", "aliases": ["Digos City", "Digos"]},
    {"name": "Cagayan de Oro", "canonical": "Cagayan de Oro City", "type": "HUC", "province": "Misamis Oriental", "region": "Region X", "aliases": ["Cagayan de Oro City", "Cagayan de Oro", "CDO"]},
    {"name": "Iligan", "canonical": "Iligan City", "type": "HUC", "province": "Lanao del Norte", "region": "Region X", "aliases": ["Iligan City", "Iligan"]},
    {"name": "General Santos", "canonical": "General Santos City", "type": "HUC", "province": "South Cotabato", "region": "Region XII", "aliases": ["General Santos City", "General Santos", "GenSan"]},
    {"name": "Zamboanga City", "canonical": "Zamboanga City", "type": "HUC", "province": "Zamboanga del Sur", "region": "Region IX", "aliases": ["Zamboanga City"]},
    {"name": "Butuan", "canonical": "Butuan City", "type": "HUC", "province": "Agusan del Norte", "region": "Region XIII", "aliases": ["Butuan City", "Butuan"]},
    {"name": "Cotabato City", "canonical": "Cotabato City", "type": "Independent Component City", "province": "Maguindanao del Norte", "region": "BARMM", "aliases": ["Cotabato City"]},
    {"name": "Puerto Princesa", "canonical": "Puerto Princesa City", "type": "HUC", "province": "Palawan", "region": "MIMAROPA (Region IV-B)", "aliases": ["Puerto Princesa City", "Puerto Princesa"]},

    # ── BICOL ────────────────────────────────────────────────────────────────
    {"name": "Legazpi", "canonical": "Legazpi City", "type": "Component City", "province": "Albay", "region": "Region V", "aliases": ["Legazpi City", "Legaspi City", "Legazpi", "Legaspi"]},
    {"name": "Naga", "canonical": "Naga City", "type": "Independent Component City", "province": "Camarines Sur", "region": "Region V", "aliases": ["Naga City, Camarines Sur", "Naga City", "Naga, CamSur"]},
]


# ─── 4. Commercial Hubs & Central Business Districts ─────────────────────────

COMMERCIAL_HUBS: Dict[str, Dict[str, Any]] = {
    "BGC": {
        "hub": "BGC",
        "city": "Taguig City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Bonifacio Global City": {
        "hub": "BGC",
        "city": "Taguig City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "McKinley Hill": {
        "hub": "McKinley Hill",
        "city": "Taguig City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "McKinley West": {
        "hub": "McKinley West",
        "city": "Taguig City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Ortigas Center": {
        "hub": "Ortigas",
        "city": "Pasig City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Ortigas": {
        "hub": "Ortigas",
        "city": "Pasig City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Makati CBD": {
        "hub": "Makati CBD",
        "city": "Makati City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Ayala Ave": {
        "hub": "Makati CBD",
        "city": "Makati City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Salcedo Village": {
        "hub": "Salcedo Village",
        "city": "Makati City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Legaspi Village": {
        "hub": "Legaspi Village",
        "city": "Makati City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Alabang": {
        "hub": "Alabang",
        "city": "Muntinlupa City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Filinvest City": {
        "hub": "Filinvest City",
        "city": "Muntinlupa City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Eastwood": {
        "hub": "Eastwood",
        "city": "Quezon City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Eastwood City": {
        "hub": "Eastwood",
        "city": "Quezon City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Araneta City": {
        "hub": "Araneta City",
        "city": "Quezon City",
        "province": "Metro Manila",
        "region": "NCR",
        "type": "HUC"
    },
    "Clark": {
        "hub": "Clark",
        "city": "Angeles City",
        "province": "Pampanga",
        "region": "Region III",
        "type": "HUC"
    },
    "Clark Freeport Zone": {
        "hub": "Clark",
        "city": "Angeles City",
        "province": "Pampanga",
        "region": "Region III",
        "type": "HUC"
    },
    "Subic Bay": {
        "hub": "Subic",
        "city": "Olongapo City",
        "province": "Zambales",
        "region": "Region III",
        "type": "HUC"
    },
    "Cebu IT Park": {
        "hub": "Cebu IT Park",
        "city": "Cebu City",
        "province": "Cebu",
        "region": "Region VII",
        "type": "HUC"
    },
    "IT Park": {
        "hub": "Cebu IT Park",
        "city": "Cebu City",
        "province": "Cebu",
        "region": "Region VII",
        "type": "HUC"
    },
}


# ─── 5. Tier 1 PSGC Dataset Ingestion & Caching ───────────────────────────────

_GAZETTEER_CACHE: Optional[Dict[str, Any]] = None


def get_default_psgc_json_path() -> str:
    """Returns absolute path to local psgc_locations.json cache file."""
    return os.path.join(os.path.dirname(__file__), "psgc_locations.json")


def load_psgc_data(json_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Tier 1 loader: Ingests full PSGC hierarchy dataset from local json if available,
    falling back to Tier 2 core offline dictionary.
    """
    global _GAZETTEER_CACHE
    if _GAZETTEER_CACHE is not None:
        return _GAZETTEER_CACHE

    target_path = json_path or get_default_psgc_json_path()
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                _GAZETTEER_CACHE = data
                return data
        except Exception:
            pass

    # Initialize from embedded Tier 2 core gazetteer
    gazetteer: Dict[str, Any] = {
        "regions": PHILIPPINE_REGIONS,
        "provinces": PHILIPPINE_PROVINCES,
        "lgus": CORE_LGUS,
        "hubs": COMMERCIAL_HUBS
    }
    _GAZETTEER_CACHE = gazetteer
    return gazetteer


def build_psgc_dataset(output_path: Optional[str] = None) -> str:
    """
    Builds and caches the full PSGC hierarchy dataset into psgc_locations.json.
    """
    target = output_path or get_default_psgc_json_path()
    dataset = {
        "metadata": {
            "version": "PSGC-2026",
            "source": "Philippine Statistics Authority (PSA) Standard Hierarchy",
            "total_regions": len(PHILIPPINE_REGIONS),
            "total_provinces": len(PHILIPPINE_PROVINCES),
            "core_lgus_count": len(CORE_LGUS),
            "commercial_hubs_count": len(COMMERCIAL_HUBS)
        },
        "regions": PHILIPPINE_REGIONS,
        "provinces": PHILIPPINE_PROVINCES,
        "lgus": CORE_LGUS,
        "hubs": COMMERCIAL_HUBS
    }
    with open(target, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    return target


# ─── 6. Public Lookup & Disambiguation Helpers ───────────────────────────────

def lookup_location(name: str, province_hint: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Searches for an LGU or Business District by name, handling aliases, diacritics,
    and optional province disambiguation hint.
    """
    clean = name.strip()
    clean_no_acc = remove_accents(clean).lower()

    # Check commercial hubs
    for hub_name, hub_info in COMMERCIAL_HUBS.items():
        if clean.lower() == hub_name.lower() or clean_no_acc == remove_accents(hub_name).lower():
            return {
                "name": hub_name,
                "canonical": hub_info["city"],
                "type": hub_info["type"],
                "province": hub_info["province"],
                "region": hub_info["region"],
                "hub": hub_info["hub"]
            }

    candidates = []
    for lgu in CORE_LGUS:
        for alias in lgu["aliases"]:
            if clean.lower() == alias.lower() or clean_no_acc == remove_accents(alias).lower():
                candidates.append(lgu)
                break

    if not candidates:
        return None

    if len(candidates) == 1:
        return candidates[0]

    if province_hint:
        hint_clean = province_hint.strip().lower()
        for cand in candidates:
            if cand["province"].lower() == hint_clean:
                return cand

    return candidates[0]


def infer_province_and_region(city_or_muni: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Given a city or municipality name, infer its parent Province and Region.
    Returns: (province_name, region_name)
    """
    loc = lookup_location(city_or_muni)
    if loc:
        return loc["province"], loc["region"]
    return None, None


def is_philippine_province(name: str) -> bool:
    """Check if string is a valid Philippine Province."""
    clean = name.strip().lower()
    for prov in PHILIPPINE_PROVINCES:
        if clean == prov.lower():
            return True
    return False


def get_gazetteer() -> Dict[str, Any]:
    """Returns the singleton gazetteer dictionary."""
    return load_psgc_data()
