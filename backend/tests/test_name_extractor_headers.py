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

if __name__ == "__main__":
    unittest.main()
