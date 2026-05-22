from app.extractors.nlp.nlp_engine import extract_all
from app.extractors.content.education_extractor import extract_education

resumes = [
    "I have a BSCS from UP Diliman. Graduated in 2021.",
    "EDUCATION\n- BSIT, Mapua University (2020)\n- STEM Strand, FEU Tech 2016",
    "Graduated with a BSCpE at PUP in 2019.",
    "Associate in Computer Technology - DLSU",
    "Bachelor of Science in Information Systems - Ateneo de Manila University 2018",
    "HUMSS - UST 2015"
]

for r in resumes:
    print(f"Resume: {r}")
    print(f"NLP Extracted: {extract_all(r)['education']}")
    print(f"Final Extracted: {extract_education(r)}")
    print("-" * 50)
