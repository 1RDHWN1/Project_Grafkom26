# Grafkom - Simulasi Gerhana 3D

Project Python/OpenGL untuk simulasi gerhana dengan dua sudut pandang: scene kota dan scene luar angkasa.

## Prasyarat

- Python 3.10 atau lebih baru
- Driver GPU/OpenGL yang aktif
- Audio asset `city.mp3` dan `space.mp3` tetap berada di root project

## Setup di Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Jika PowerShell menolak aktivasi virtual environment, jalankan:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Lalu aktifkan ulang:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Setup di macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Struktur File Utama

- `main.py`: entry point aplikasi dan loop simulasi
- `config.py`: konfigurasi ukuran window, warna, orbit, dan performa
- `gl_engine.py`: helper matematika dan primitive drawing OpenGL
- `city_scene.py`: objek dan rendering scene kota
- `space_scene.py`: controller gerhana dan rendering scene luar angkasa
- `city.mp3`, `space.mp3`: audio untuk scene

## Catatan Git

Virtual environment, cache Python, dan folder editor sudah masuk `.gitignore`.

Kalau sebelumnya folder virtual environment sudah terlanjur masuk Git, bersihkan dari index tanpa menghapus file lokal:

```powershell
git rm -r --cached venv312 .venv venv312_broken __pycache__
git add .gitignore README.md requirements.txt
```
