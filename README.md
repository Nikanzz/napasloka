# NapasLoka

Sistem prediksi konsentrasi polutan karbon monoksida (CO) dan karbon dioksida (CO2) satu jam ke depan untuk 15 lokasi di wilayah Jabodetabek. Model menggunakan algoritma regresi XGBoost dan LightGBM dengan fitur lag temporal, dilengkapi atribusi kontribusi fitur berbasis TreeSHAP serta antarmuka Progressive Web App (PWA).

Repositori ini memuat seluruh alur kerja penelitian: pengambilan data dari API, pembersihan data terisolasi per lokasi, 120 pengujian eksperimen hyperparameter, pembuatan registri model juara, retraining model final pada data historis penuh, backend REST API berbasis FastAPI, dan frontend PWA.

---

## Ringkasan Teknis

- **Target Prediksi**: CO (`carbon_monoxide`, µg/m³) dan CO2 (`carbon_dioxide`, ppm). Masing-masing polutan dilatih terpisah agar tidak saling mengganggu distribusi nilai target.
- **Horizon Waktu**: Satu jam berikutnya ($t$) berdasarkan nilai masa lalu ($t-1, t-2, t-3$).
- **Skenario Masukan**:
  - **Skenario 1**: 3 fitur lag polutan murni ($t-1, t-2, t-3$).
  - **Skenario 2**: 15 fitur gabungan, berisi 3 lag polutan dan 12 lag variabel cuaca (temperatur, kelembaban udara, curah hujan, kecepatan angin pada $t-1, t-2, t-3$).
- **Cakupan Wilayah**: 15 titik koordinat pengamatan di DKI Jakarta, Bogor, Depok, Tangerang, dan Bekasi (konfigurasi lengkap berada di `configs/locations.yaml`).
- **Sumber Data**: Penarikan data Open-Meteo (CAMS Air Quality dan Historical Weather) rentang 26 Oktober 2024 pukul 07:00 WIB sampai 26 Oktober 2026 pukul 18:00 WIB, menghasilkan 17.532 baris pengamatan per lokasi.
- **Validasi Silang & Tuning**: Pembagian data 80% train dan 20% test secara kronologis tanpa pengacakan posisi baris. Penyetelan parameter menggunakan `RandomizedSearchCV` dengan skema `TimeSeriesSplit` sebanyak 3 fold dan batas ukuran jendela latih tetap (`max_train_size = 3108`).

---

## Struktur Direktori

```text
napasloka/
├── artifacts/              # Berkas luaran sistem
│   ├── experiments/        # 120 folder model uji (joblib, metrik, prediksi, bobot SHAP)
│   ├── final/              # 60 model produksi terlatih pada 100% data historis
│   ├── registry/           # best_models.json (pemetaan model juara per skenario)
│   └── summary_metrics.csv # Rekap metrik performa 120 eksperimen
├── backend/                # Layanan FastAPI
│   └── app/
│       ├── api/            # Endpoint prediksi, evaluasi, dan interpretasi SHAP
│       ├── services/       # Logika bisnis, pemuatan cache model, dan pembaca data
│       └── main.py         # Inisialisasi aplikasi FastAPI dan mounting PWA
├── configs/                # Berkas konfigurasi YAML
│   ├── locations.yaml      # Daftar 15 koordinat stasiun Jabodetabek
│   ├── scenarios.yaml      # Definisi kolom fitur tiap skenario
│   └── tuning.yaml         # Ruang pencarian parameter dan konfigurasi TimeSeriesSplit
├── data/
│   ├── raw/                # Berkas unduhan mentah API Open-Meteo
│   └── processed/          # Dataset gabungan hasil pembersihan per polutan
├── frontend/               # Kode sumber PWA (HTML, CSS native, vanilla JavaScript)
├── notebooks/              # Lembar kerja Jupyter (analisis eksplorasi, komparasi, SHAP)
├── src/                    # Pipeline kode sumber Python
│   ├── data/               # fetch_data.py dan clean_data.py
│   ├── features/           # lag_features.py dan scenarios.py
│   ├── models/             # estimators.py, experiments.py, evaluate_model.py, train_model.py
│   └── utils/              # Pengelola berkas konfigurasi dan pembuat identifier
├── run_api.py              # Skrip peluncur server web Uvicorn
└── run_pipeline.py         # Skrip otomatisasi end-to-end pipeline penelitian
```

---

## Pemasangan & Persiapan Lingkungan

Jalankan perintah berikut melalui Windows PowerShell di dalam folder `napasloka`:

```powershell
# 1. Buat dan aktifkan virtual environment Python
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Perbarui pip dan pasang pustaka yang dibutuhkan
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## Menjalankan Pipeline Machine Learning

Seluruh proses eksperimen dan pelatihan model produksi dikendalikan lewat satu perintah terpusat:

```powershell
python run_pipeline.py
```

Skrip ini menjalankan tahapan berikut secara berurutan:
1. Mengecek ketersediaan data mentah di `data/raw/` (mengunduh otomatis via API bila belum tersedia).
2. Membersihkan duplikasi, memverifikasi kelengkapan nilai, dan menggabungkan data cuaca dengan polutan ke `data/processed/`.
3. Memeriksa ketersediaan artefak 120 eksperimen riset di `artifacts/experiments/`. Bila sudah ada, proses pelatihan dilewati secara otomatis via mekanisme caching.
4. Menyusun rekapitulasi seluruh skor evaluasi ke `artifacts/summary_metrics.csv`.
5. Memilih model dengan nilai MAE dan RMSE terendah untuk tiap kombinasi stasiun, lalu melatih ulang 60 model produksi ke `artifacts/final/`.

Untuk memaksa sistem melatih ulang seluruh model dari nol, buka `run_pipeline.py` dan ubah variabel:
```python
FORCE_RETRAIN = True
```

---

## Menjalankan Aplikasi Web & API

Jalankan server aplikasi lokal:

```powershell
python run_api.py
```

Setelah server aktif:
- Buka antarmuka PWA di peramban: `http://127.0.0.1:8000/`
- Buka dokumentasi interaktif Swagger API: `http://127.0.0.1:8000/docs`

Backend FastAPI langsung melayani halaman frontend PWA secara mandiri tanpa memerlukan server web terpisah.

---

## Analisis Notebook Jupyter

Eksplorasi data dan visualisasi grafik Bab 4 skripsi dapat dibuka melalui folder `notebooks/`:
- `01_data_exploration.ipynb`: Statistik deskriptif dan uji korelasi variabel.
- `02_model_comparison.ipynb`: Perbandingan performa XGBoost vs LightGBM di 15 lokasi.
- `03_scenario_comparison.ipynb`: Analisis pengaruh penambahan fitur meteorologi Skenario 1 vs Skenario 2.
- `04_computation_time_comparison.ipynb`: Pengukuran durasi waktu training dan latency inferensi.
- `05_shapley_interpretation_model.ipynb`: Analisis atribusi fitur global dan visualisasi waterfall plot lokal berbasis TreeSHAP.
