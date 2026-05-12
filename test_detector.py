import unittest
from pathlib import Path
from detector import extract_text_from_bytes

class TestPlagiarismDetector(unittest.TestCase):

    def test_txt_file(self):
        content = b"This is a test text file."
        result = extract_text_from_bytes("test.txt", content)
        self.assertEqual(result, "This is a test text file.")

    def test_pdf_file(self):
        with open("sample.pdf", "rb") as f:
            content = f.read()
        result = extract_text_from_bytes("sample.pdf", content)
        self.assertIn("Sample PDF content", result)

    def test_docx_file(self):
        with open("sample.docx", "rb") as f:
            content = f.read()
        result = extract_text_from_bytes("sample.docx", content)
        self.assertIn("Sample DOCX content", result)

if __name__ == "__main__":
    unittest.main()