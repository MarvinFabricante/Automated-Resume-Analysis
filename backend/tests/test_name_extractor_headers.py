import sys
import unittest
sys.path.insert(0, 'backend')

from app.extractors.content.name_extractor import extract_fullname
from app.extractors.content.content_extractor import extract_content

class TestNameAndHeaderExtraction(unittest.TestCase):
    def test_standard_order(self):
        text = """John Paul T. Basagre
E-commerce Specialist
johnny.basagre@gmail.com
09171234567
Batangas, Philippines
EDUCATION
Bachelor of Science in Information Technology
EXPERIENCE
E-commerce Specialist at Retail Corp (2021 - Present)
SKILLS
Shopify, SEO, Digital Marketing, Inventory Management
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")
        content = extract_content(text)
        self.assertEqual(content.get("email"), "johnny.basagre@gmail.com")
        self.assertTrue("0917" in content.get("phone", ""))
        self.assertTrue(len(content.get("skills_list", [])) >= 2)

    def test_surname_first_with_comma(self):
        text = """Basagre, John Paul T.
E-commerce Specialist
johnny.basagre@gmail.com
+63 917 123 4567
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_all_caps(self):
        text = """JOHN PAUL T. BASAGRE
E-COMMERCE SPECIALIST
johnny.basagre@gmail.com
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_inline_dash_title(self):
        text = """John Paul T. Basagre - E-commerce Specialist
johnny.basagre@gmail.com
09185551234
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_merged_title_on_same_line(self):
        # Solves: 'John Paul T. Basagre E-commerce Specialist' merged in PDF/DOCX
        text = """John Paul T. Basagre E-commerce Specialist
johnny.basagre@gmail.com
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_title_before_name(self):
        text = """E-commerce Specialist
John Paul T. Basagre
johnny.basagre@gmail.com
09191234567
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_pipe_separated_header(self):
        text = """John Paul T. Basagre | Web Developer | johnny.basagre@gmail.com | 09171234567"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_split_across_two_lines_surname_first(self):
        text = """Basagre
John Paul T.
E-commerce Specialist
johnny.basagre@gmail.com
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_split_across_two_lines_given_first(self):
        text = """John Paul T.
Basagre
E-commerce Specialist
johnny.basagre@gmail.com
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_title_with_typo(self):
        # Example from prompt: 'Basagre E-commerse Specialist'
        text = """John Paul T. Basagre
Basagre E-commerse Specialist
johnny.basagre@gmail.com
"""
        extracted = extract_fullname(text)
        self.assertEqual(extracted, "John Paul T. Basagre")

    def test_other_realistic_candidate_headers(self):
        # 1. Engineering candidate
        t1 = "Maria Theresa G. Santos, CPA\nSenior Accounting Manager\nmaria.santos@gmail.com"
        self.assertTrue(extract_fullname(t1) in ("Maria Theresa G. Santos", "Maria Theresa G. Santos, CPA"))

        # 2. Plant operator
        t2 = "DELA CRUZ, JUAN M.\nMachine Operator\njuan.delacruz@yahoo.com"
        self.assertEqual(extract_fullname(t2), "Juan M. Dela Cruz")

        # 3. Graduate / Intern
        t3 = "Pedro Dimagiba Jr. - Electrical Engineering Intern\npedro.dimagiba@gmail.com"
        self.assertEqual(extract_fullname(t3), "Pedro Dimagiba Jr.")

    def test_autofill_accuracy_regressions(self):
        # 1. School + Year on line 1, Degree on line 2 must NOT put school name into degree
        #    and unbulleted responsibility lines must NOT be extracted as Company Name
        resume_text = """John Paul T. Basagre
E-commerce Specialist
johnny.basagre@gmail.com
09171234567
Teresa, Rizal

EXPERIENCE
Customer Service Representative
May 2026 - Nov 2026
Reviewed orders, invoices, and customer records for accuracy and corrected errors, including wrong
shipping addresses
Verified product information and stock details before responding

EDUCATION
STI Colleges Ortigas-Cainta (2023)
Bachelor of Science in Computer Science

SKILLS
E-commerce Operations: Order creation, cancellation, and tracking, invoicing, gift cards, refunds,
subscriptions, inventory and stock checks, 3PL coordination, address corrections
Tools & Platforms: Kustomer, Shopify, Stripe, Extole, LoyaltyLion, Internal Admin
Dashboard
Technical: Troubleshooting (Wi-Fi, NFC, Audio, Software/Hardware), Remote
device diagnostics
Soft Skills: Multi-chat handling (3+
concurrent), Order and delivery issue
resolution, Communication, Attention to
detail, Adaptability
"""
        extracted = extract_content(resume_text)
        self.assertEqual(extracted.get("fullname"), "John Paul T. Basagre")
        self.assertEqual(extracted.get("degree"), "Bachelor of Science in Computer Science")
        self.assertIn("STI College", extracted.get("college", ""))
        self.assertEqual(extracted.get("company"), "")
        # Ensure broken fragments like "Creation", "And Tracking", "Concurrent)", "Detail" are not in skills_list
        skills_lower = {s.lower() for s in extracted.get("skills_list", [])}
        self.assertNotIn("creation", skills_lower)
        self.assertNotIn("and tracking", skills_lower)
        self.assertNotIn("concurrent)", skills_lower)
        self.assertNotIn("detail", skills_lower)

    def test_parenthetical_company_location_and_compound_role_titles(self):
        resume_text = """Paulo M. Villanueva
paulo.villanueva.qa@email.com
09181234567

WORK EXPERIENCE
Quality Assurance / Quality Control Inspector
Rizal Packaging & Industrial Solutions Inc. (Taytay, Rizal)
Nov 2025 - Nov 2026 (1 year)
- Inspected packaging materials and reported defects.

EDUCATION
Bachelor of Science in Industrial Technology
Technological University of the Philippines (2024)

SKILLS
Quality Control, ISO 9001, Defect Inspection, Microsoft Excel
"""
        extracted = extract_content(resume_text)
        self.assertEqual(extracted.get("company"), "Rizal Packaging & Industrial Solutions Inc.")
        self.assertNotIn("(Taytay", extracted.get("company", ""))

if __name__ == "__main__":
    unittest.main()
