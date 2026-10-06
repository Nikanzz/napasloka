# Direktori Notebooks 📓

Direktori ini berisi notebook Jupyter eksperimen yang disusun secara modular dan berurutan mengikuti kaidah **Cookiecutter Data Science (CCDS)**. Seluruh logika inti (seperti pembentukan lag, tuning, pelatihan, dan inferensi) tetap diimplementasikan di dalam modul `src/` dan diimpor ke dalam notebook.

## Daftar Alur Eksperimen

1. `01_data_exploration.ipynb`: Eksplorasi data mentah, visualisasi distribusi polutan & meteorologi, serta matriks korelasi.
2. `02_feature_analysis.ipynb`: Analisis autokorelasi (ACF), pembentukan fitur lag ($t-1$ s.d. $t-3$), dan pembagian kronologis (80:20).
3. `03_baseline_model.ipynb`: Pemodelan Naive Persistence Baseline sebagai tolok ukur benchmark performa.
4. `04_model_comparison.ipynb`: Pelatihan dan perbandingan model Machine Learning (LightGBM vs. XGBoost) dengan TimeSeriesSplit cross-validation.
5. `05_results_visualization.ipynb`: Visualisasi performa data uji (Aktual vs. Prediksi) dan interpretabilitas TreeSHAP (nilai lokal & global).

## Panduan Eksekusi
- **Lingkungan Lokal:** Buka notebook di VS Code atau Jupyter Lab, pilih kernel Python virtual environment (`.venv`), dan jalankan sel secara berurutan.
- **Google Colab:** Notebook dilengkapi dengan mekanisme inisialisasi lingkungan otomatis (*dual-environment*).
