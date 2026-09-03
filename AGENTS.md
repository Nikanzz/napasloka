# AGENTS.md — Pedoman Repository NapasLoka

Instruksi ini berlaku untuk seluruh repository. Baca `docs/research-spec.md` dan konfigurasi terkait sebelum mengubah implementasi.

## Invariants penelitian

1. Jangan mengubah scope penelitian tanpa instruksi eksplisit.
2. Target hanya CO atau CO2 dan dimodelkan terpisah.
3. Forecast horizon = satu jam berikutnya.
4. Input history = tiga jam sebelumnya.
5. Scenario 1 = 3 lag pollutant.
6. Scenario 2 = 3 lag pollutant + 12 lag meteorological = 15 features.
7. Algorithms = XGBoost dan LightGBM.
8. Jangan random shuffle time-series.
9. Test set tidak boleh digunakan untuk tuning.
10. Gain-based feature importance = baseline interpretation.
11. SHAP = primary explainability method.
12. Jangan menyimpulkan SHAP sebagai causal relationship.
13. Frontend = vanilla HTML/CSS/JS PWA + Plotly.js.
14. Backend = FastAPI.
15. Jangan menambahkan manual coordinate input.
16. Jangan menambahkan early-warning system.
17. Jangan mengganti scope menjadi realtime sensor system.
18. Jangan mengarang data, lokasi, koordinat, model result atau metrics.
19. Jangan menjalankan training berat tanpa instruksi.
20. Semua eksperimen harus reproducible dan resumable.

## Aturan implementasi

- Perlakukan `configs/features.yaml` sebagai sumber tunggal definisi feature schema.
- Simpan data mentah tanpa modifikasi; hasil setiap tahap masuk ke direktori data yang sesuai.
- Gunakan urutan pipeline dalam `docs/research-spec.md` dan validasi data sebelum integrasi.
- Gunakan identifier dari `ml_pipeline.utils.identifiers`; jangan membuat format experiment ID lain secara lokal.
- Simpan artefak per `location/pollutant/scenario/algorithm` dan perbarui registry secara atomik.
- Jangan memasukkan dataset besar, model terlatih, secrets, atau hasil eksperimen ke Git.
- Tambahkan test untuk perubahan perilaku dan jangan menggunakan angka hasil penelitian palsu sebagai fixture.
- Jaga modul tetap generik; jangan membuat file Python terpisah untuk setiap kombinasi eksperimen.
