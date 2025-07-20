from PyPDF2 import PdfMerger, PdfReader


def append_pdfs(pdf_list, output_path):
    merger = PdfMerger()
    for pdf in pdf_list:
        try:
            merger.append(pdf)
        except Exception as e:
            print(f"Error appending {pdf}: {e}")
    merger.write(output_path)
    merger.close()
    # TODO: handle success/failure notifications


def decrypt_pdf(pdf_path, password=""):
    reader = PdfReader(pdf_path)
    if reader.is_encrypted:
        result = reader.decrypt(password)
        return result
    return True

def load_pdf_into_viewer():
    pass