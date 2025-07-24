# Tetra

**Tetra** is a cross-platform PDF utility built with Python and Kivy. It offers a minimal, user-friendly interface for selecting, viewing, and merging PDF files; Designed to run on both desktops and mobile devices.

This project is in active development and currently targets desktop platforms. Android support is planned for later versions.

---

## 🔧 Features

- Filepicker for mobile and desktop
- View basic file info like name and size
- Merge selected PDFs into a single document
- Kivy-native UI
- Portable and meant for offline use

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
