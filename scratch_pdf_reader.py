import fitz
import sys

def read_pdf(file_path):
    try:
        doc = fitz.open(file_path)
        text = ''
        for page in doc:
            text += page.get_text()
        
        with open("pdf_output.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("Successfully extracted PDF text to pdf_output.txt")
    except Exception as e:
        print(f"Error with PyMuPDF: {e}")

if __name__ == "__main__":
    read_pdf(sys.argv[1])
