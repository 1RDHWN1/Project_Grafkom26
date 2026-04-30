"""
=============================================================
  FILE: config.py
  Fungsi: Menyimpan semua konstanta dasar, warna, dan 
          pengaturan simulasi. Ubah angka di sini untuk 
          menyesuaikan tampilan tanpa merusak logika utama.
=============================================================
"""

# ───────────────────────────────────────────────────────────
# 1. PENGATURAN JENDELA & APLIKASI
# ───────────────────────────────────────────────────────────
WIDTH  = 1280
HEIGHT = 720
FPS    = 60
TITLE  = "Simulasi Gerhana 3D (Optimized & Modular)"

# ───────────────────────────────────────────────────────────
# 2. PENGATURAN WARNA LANGIT (Format RGB 0.0 - 1.0)
# ───────────────────────────────────────────────────────────
# Warna langit ini akan bertransisi secara halus tergantung
# pada tingkat kegelapan gerhana (0.0 sampai 1.0)
SKY_DAY    = (0.42, 0.75, 0.98)   # Biru siang cerah
SKY_DUSK   = (0.95, 0.52, 0.18)   # Oranye hangat (saat gerhana mulai)
SKY_NIGHT  = (0.04, 0.03, 0.12)   # Ungu gelap (puncak gerhana)

# ───────────────────────────────────────────────────────────
# 3. PENGATURAN WARNA KABUT (FOG)
# ───────────────────────────────────────────────────────────
# Kabut berfungsi menyamarkan ujung peta (map) agar tidak
# terlihat terpotong secara kasar.
FOG_DAY    = (0.55, 0.80, 0.98)
FOG_DUSK   = (0.80, 0.40, 0.15)
FOG_NIGHT  = (0.02, 0.01, 0.06)

# ───────────────────────────────────────────────────────────
# 4. SIKLUS WAKTU GERHANA (Otomatis Looping)
# ───────────────────────────────────────────────────────────
ECLIPSE_CYCLE = 55.0  # Total waktu (detik) untuk 1 siklus gerhana matahari
LUNAR_CYCLE   = 75.0  # Total waktu (detik) untuk 1 siklus gerhana bulan

# ───────────────────────────────────────────────────────────
# 5. ORBIT & UKURAN BENDA LANGIT DI SCENE KOTA (In-Earth POV)
# ───────────────────────────────────────────────────────────
SUN_ORBIT_R_H = 260.0  # Radius horizontal orbit matahari di atas kota
SUN_ORBIT_R_V = 160.0  # Radius vertikal orbit matahari
SUN_SPEED     = 0.018  # Kecepatan pergerakan matahari harian
SUN_R         = 55.0   # Skala ukuran model matahari
SUN_DIST      = -900.0 # Jarak matahari ke belakang agar terlihat jauh
MOON_R_CITY   = 30.0   # Skala ukuran model bulan saat terlihat dari kota

# ───────────────────────────────────────────────────────────
# 6. ORBIT & UKURAN PLANET DI SCENE ANGKASA (Space POV)
# ───────────────────────────────────────────────────────────
EARTH_ORBIT_R   = 500.0  # Jarak Bumi saat mengelilingi pusat scene
EARTH_ORBIT_SPD = 0.012  # Kecepatan revolusi Bumi
MOON_ORBIT_R    = 110.0  # Jarak Bulan saat mengelilingi Bumi
MOON_ORBIT_SPD  = 0.09   # Kecepatan revolusi Bulan terhadap Bumi