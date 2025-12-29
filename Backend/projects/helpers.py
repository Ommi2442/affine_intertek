import platform
import subprocess
import pythoncom
from docx2pdf import convert

def convert_docx_to_pdf(docx_path: str, pdf_path: str):
    system = platform.system().lower()

    # ---------- WINDOWS (MS WORD via COM) ----------
    if system == "windows":
        pythoncom.CoInitialize()     # ✅ REQUIRED
        try:
            convert(docx_path, pdf_path)
        finally:
            pythoncom.CoUninitialize()  # ✅ REQUIRED
        return

    # ---------- LINUX (LIBREOFFICE) ----------
    if system == "linux":
        subprocess.run(
            [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                os.path.dirname(pdf_path),
                docx_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    raise RuntimeError(f"Unsupported OS for DOCX conversion: {system}")

