# Research Specification — NapasLoka

Dokumen ini adalah **single source of truth teknis** repository. Perubahan terhadap alur atau ruang lingkup penelitian harus disertai instruksi eksplisit dan pembaruan dokumen ini beserta konfigurasi terkait.

## Tujuan

NapasLoka memprediksi konsentrasi satu jam berikutnya untuk CO (µg/m³) atau CO2 (ppm) secara terpisah pada 15 lokasi penelitian di Jabodetabek. Observasi merupakan keluaran berbasis grid dari CAMS melalui Open-Meteo, bukan pembacaan sensor langsung di lokasi.

## Alur penelitian

```text
Data historis Open-Meteo/CAMS
  → Preprocessing dan validasi
  → EDA
  → Feature engineering lag
  → Pemilihan Scenario 1 atau Scenario 2
  → Chronological train/test split (tanpa shuffle)
  → Grid Search + TimeSeriesSplit pada training set saja (bila diaktifkan)
  → XGBoost Regression atau LightGBM Regression
  → Prediction pada test set
  → MAE, RMSE, MAPE, R² + training/prediction time
  → Gain feature importance (baseline) + SHAP/TreeSHAP (utama)
  → Saved artifacts dan experiment registry
  → FastAPI
  → Vanilla HTML/CSS/JS PWA + Plotly.js
```

## Data

Kolom inti adalah `datetime`, `latitude`, `longitude`, `carbon_monoxide`, `carbon_dioxide`, `temperature_2m`, `relative_humidity_2m`, `rain`, dan `wind_speed_100m`, ditambah identifier `location` untuk integrasi dan penyimpanan. Data polutan dan meteorologi disimpan utuh di `data/raw/` sebelum transformasi apa pun.

Daftar 15 lokasi belum ditetapkan dalam repository. `configs/locations.yaml` harus tetap kosong sampai nama dan koordinat tervalidasi tersedia.

## Preprocessing dan integrasi

Urutan wajib:

1. Muat data mentah tanpa mengubah sumbernya.
2. Parse `datetime` dan standardisasi ke timezone `Asia/Jakarta`.
3. Urutkan per lokasi secara kronologis.
4. Periksa timestamp duplikat, missing values, dan nilai invalid.
5. Integrasikan polutan dan meteorologi berdasarkan `location` dan `datetime`.
6. Jangan melakukan imputasi bila tidak ada missing values.
7. Jangan melakukan scaling atau penghapusan outlier otomatis.

Keputusan menangani missing/invalid/outlier harus terdokumentasi sebagai keputusan penelitian, bukan efek samping pipeline.

## Feature engineering dan target

Target pada waktu `t` adalah konsentrasi polutan satu jam setelah observasi terakhir. Input history menggunakan lag `t-3`, `t-2`, dan `t-1`:

- `scenario_1`: 3 lag target polutan.
- `scenario_2`: 3 lag target polutan + tiga lag untuk masing-masing `temperature_2m`, `relative_humidity_2m`, `rain`, dan `wind_speed_100m` = 15 fitur.

`configs/features.yaml` adalah sumber tunggal definisi schema fitur. Kode lain harus memakai `ml_pipeline.features.scenarios` dan tidak menduplikasi daftar fitur.

## Split dan tuning

Feature engineering dilakukan sebelum chronological split. Tidak ada random shuffle. Test set dipisahkan dan tidak boleh ikut dalam pemilihan hyperparameter. Bila kelak diaktifkan, tuning menggunakan `GridSearchCV` dengan `TimeSeriesSplit` hanya pada training set. Search space tetap kosong dan `enabled: false` selama Phase 0, menunggu finalisasi setelah seminar proposal.

## Model dan matriks eksperimen

Pipeline generik menerima `location`, `pollutant`, `scenario`, dan `algorithm`. Kombinasi 15 lokasi × 2 polutan × 2 scenario × 2 algoritma menghasilkan 120 model final tanpa membuat 120 file kode. Setiap kombinasi dapat memiliki best hyperparameter sendiri.

## Evaluasi dan interpretasi

Evaluasi melaporkan MAE, RMSE, MAPE, R², training time, dan prediction/test time dengan pengukur waktu yang sama untuk kedua algoritma. Gain-based feature importance adalah baseline interpretasi, bukan validasi SHAP. SHAP/TreeSHAP adalah metode utama; global importance memakai mean absolute SHAP dan interface harus dapat dikembangkan untuk local explanation. Nilai SHAP tidak menyatakan hubungan sebab-akibat.

## Artefak dan resumability

Setiap eksperimen disimpan independen di:

```text
artifacts/experiments/<location>/<pollutant>/<scenario>/<algorithm>/
```

Direktori tersebut nantinya dapat berisi `model.*`, `best_params.json`, `metrics.json`, `predictions.csv`, `feature_importance.csv`, `shap_global.csv`, dan `experiment_metadata.json`. Registry mencatat status `pending`, `running`, `completed`, atau `failed`, sehingga eksperimen yang selesai tidak diulang setelah proses terhenti.

## Penyajian

FastAPI menyediakan data penelitian dan artefak berdasarkan empat dimensi eksperimen. PWA tidak meminta koordinat, konsentrasi, atau meteorologi manual; pengguna hanya memilih opsi yang tersedia dan rentang waktu yang didukung. Plotly.js disiapkan untuk actual-vs-predicted, perbandingan model, feature importance, dan visualisasi SHAP yang sesuai.
