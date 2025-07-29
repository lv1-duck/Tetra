# Tetra

**Tetra** is a cross-platform PDF utility built with Python and Kivy. It offers a minimal, user-friendly interface for selecting, viewing, and merging PDF files; Designed to run on both desktops and mobile devices.

This project relies on a diverse set of open-source Python libraries to support cross-platform development, particularly targeting Android via Kivy and Buildozer. The core UI framework is Kivy (2.3.1) for creating mobile interfaces. Buildozer, along with python-for-android, handles packaging for Android deployment. PDF processing is done through PyMuPDF (fitz), which allows fast manipulation and rendering of PDF files without requiring external dependencies. Pillow is used for image handling, while Plyer bridges access to platform-native features like storage permissions and access on mobile devices. 

This is more of a proof-of-concept thing—a prototype, and it is only made for fun and learning purposes with no plans of ever scaling. But this project is still in active development. Feedbacks and contributions are greatly appreciated.

---

## 🔧 Features

- Filepicker for mobile and desktop
- View basic file info like name and size
- Merge selected PDFs into a single document
- Kivy-native UI
- Built for offline use

---

## Some features/improvements that would be awesome to make.

- Better UI design
  
---


## 🖥️ Running on Desktop

### Requirements

- Python 3.10 or higher
- [pip](https://pip.pypa.io/)
- Dependencies listed in `requirements.txt`

### Setup Instructions

```bash
# Clone the repository
git clone https://github.com/yourusername/tetra.git
cd tetra

# Create and activate a virtual environment (optional but recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python main.py
