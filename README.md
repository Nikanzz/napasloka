# NapasLoka

Scaffold Phase 0 untuk penelitian S1 berjudul **“Pengembangan Sistem Prediksi Konsentrasi CO dan CO2 Berbasis Explainable AI dengan XGBoost dan LightGBM Menggunakan Data Historis Polutan dan Meteorologi di Wilayah Jabodetabek.”**

Repository ini baru menyediakan kontrak konfigurasi, pipeline modular, registry eksperimen resumable, FastAPI minimal, skeleton PWA, dan test dasar. Belum ada dataset yang diunduh, model yang dilatih, tuning yang dijalankan, maupun hasil ilmiah yang dihasilkan.

## Ruang lingkup tetap

- Target CO (`carbon_monoxide`, µg/m³) dan CO2 (`carbon_dioxide`, ppm) dimodelkan terpisah.
- Horizon prediksi adalah satu jam berikutnya menggunakan tiga observasi sebelumnya.
- Scenario 1 memiliki 3 lag polutan; Scenario 2 memiliki 3 lag polutan dan 12 lag meteorologi.
- Algoritma yang disiapkan hanya XGBoost Regression dan LightGBM Regression.
- Pembagian train/test harus kronologis tanpa random shuffle.
- Tuning hanya pada training set dengan Grid Search dan `TimeSeriesSplit`; tuning dinonaktifkan pada Phase 0.

Spesifikasi teknis lengkap berada di [docs/research-spec.md](docs/research-spec.md).

## Setup Windows (PowerShell)

Jalankan perintah dari folder `napasloka`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Salin konfigurasi environment bila diperlukan:

```powershell
Copy-Item .env.example .env
```

## Menjalankan test

```powershell
python -m pytest
```

## Menjalankan FastAPI

```powershell
python scripts/run_api.py
```

API tersedia di `http://127.0.0.1:8000`; dokumentasi interaktif berada di `http://127.0.0.1:8000/docs`.

Endpoint Phase 0:

- `GET /api/v1/health`
- `GET /api/v1/config/options`
- `POST /api/v1/predict` (mengembalikan `MODEL_NOT_AVAILABLE` sampai artefak model tersedia)

## Membuka frontend PWA

Gunakan server statis, bukan membuka file HTML langsung:

```powershell
python -m http.server 5500 --directory frontend
```

Buka `http://127.0.0.1:5500`. Pastikan API juga berjalan jika ingin memuat opsi konfigurasi.

## Status Phase 0

File di `configs/locations.yaml` sengaja belum berisi lokasi. Isi hanya setelah nama dan koordinat 15 lokasi penelitian disahkan. Search space tuning, proses training penuh, prediksi aktual, feature importance, dan analisis SHAP masih berupa interface/placeholder yang terdokumentasi.
