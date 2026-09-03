# Architecture

NapasLoka memisahkan konfigurasi (`configs`), data dan machine-learning pipeline (`ml_pipeline`), adapter HTTP (`backend`), antarmuka pengguna (`frontend`), serta keluaran eksperimen (`artifacts`).

Dependency mengalir satu arah: API memanggil service; service membaca konfigurasi/artefak atau memanggil pipeline; pipeline tidak bergantung pada FastAPI maupun frontend. Registry dan identifier eksperimen dipusatkan agar training bertahap dapat dilanjutkan dengan aman.
