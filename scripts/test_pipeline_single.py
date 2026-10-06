import sys
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.paths import DATA_DIR
from src.features.scenarios import resolve_scenario
from src.features.lag_features import create_lag_features
from src.data.preprocessing import chronological_train_test_split

def main():
    print("=== MVG Tahap 1: Verifikasi Pipeline Data ===")

    # Data loading
    co_dataset_path = DATA_DIR / "processed" / "jabodetabek_co_dataset.csv"
    if not co_dataset_path.exists():
        print(f"Error: Dataset {co_dataset_path} belum ada. Jalankan fetch_data.py terlebih dahulu.")
        return

    print("1. Memuat dataset...")
    df = pd.read_csv(co_dataset_path)
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True).dt.tz_convert("Asia/Jakarta")

    # Filter single location (Taman Kamal)
    location_id = "-6.1_106.7"
    df_loc = df[df["location"] == location_id].copy()

    if df_loc.empty:
        print(f"Error: Tidak ada data dengan location == '{location_id}'. Pastikan formatnya benar.")
        return

    df_loc = df_loc.sort_values("datetime").reset_index(drop=True)

    print(f"   => Data lokasi {location_id} berhasil dimuat. Total baris awal: {len(df_loc)}")

    # Feature engineering (Scenario 1)
    print("\n2. Melakukan Feature Engineering (Skenario 1 - CO Lags)...")

    expected_features = resolve_scenario("carbon_monoxide", "scenario_1")
    df_features = create_lag_features(
        df_loc, 
        pollutant="co", 
        scenario="scenario_1",                                                                  
        drop_incomplete_rows=True
    )

    print(f"   => Baris setelah membuang NaN awal akibat pergeseran lag: {len(df_features)}")

    print("\n   => Cuplikan fitur 5 baris pertama (Apakah lag t-3..t-1 sejajar dengan datetime sekarang?):")
    cols_to_show = ["datetime", "carbon_monoxide"] + list(expected_features.feature_names)
    print(df_features[cols_to_show].head())

    # Train-test split
    print("\n3. Membagi Data secara Kronologis (80% Train, 20% Test)...")
    train_df, test_df = chronological_train_test_split(df_features, test_fraction=0.2)

    print(f"   => Total Data Latih (Train): {len(train_df)} baris")
    print(f"   => Total Data Uji (Test): {len(test_df)} baris")

    print("\n   => Akhir Data Latih (Train):")
    print(train_df[["datetime", "carbon_monoxide"]].tail())

    print("\n   => Awal Data Uji (Test):")
    print(test_df[["datetime", "carbon_monoxide"]].head())

    print("\nVerifikasi Tahap 1 Selesai! Data siap dilatih.")

    print("\n=== MVG Tahap 2: Pelatihan dan Evaluasi 1 Model XGBoost ===")

    from src.modeling.training import create_estimator, train_model
    from src.modeling.prediction import predict
    from src.evaluation.metrics import calculate_regression_metrics

    # Model training & evaluation (XGBoost baseline)
    target_col = "carbon_monoxide"
    feature_cols = list(expected_features.feature_names)

    X_train = train_df[feature_cols]
    y_train = train_df[target_col]

    X_test = test_df[feature_cols]
    y_test = test_df[target_col]

    print("\n4. Menginisialisasi Model XGBoost...")
    model = create_estimator("xgboost", parameters={"random_state": 42})
    
    print("\n5. Melatih Model (XGBoost)...")
    train_result = train_model(model, X_train, y_train)
    print(f"   => Pelatihan selesai dalam {train_result.training_time_seconds:.3f} detik.")
    
    print("\n6. Melakukan Prediksi pada Data Uji (Test)...")
    predict_result = predict(train_result.model, X_test)
    print(f"   => Prediksi selesai dalam {predict_result.prediction_time_seconds:.3f} detik.")
    
    print("\n7. Menghitung Metrik Evaluasi...")
    try:
        metrics = calculate_regression_metrics(y_test, predict_result.values)
        for metric_name, metric_value in metrics.items():
            print(f"   => {metric_name.upper()}: {metric_value:.4f}")
    except ValueError as e:
        print(f"   => Peringatan Metrik: {e}")
        
    print("\nVerifikasi Tahap 2 Selesai! Model XGBoost berhasil dilatih dan dievaluasi dari ujung ke ujung.")

    print("\n=== MVG Tahap 3: Interpretasi Model dengan SHAP (Explainable AI) ===")
    from src.interpretation.shap_analysis import calculate_tree_shap, mean_absolute_shap

    # SHAP analysis
    print("\n8. Menghitung SHAP Values untuk Data Uji (Test)...")
    shap_values = calculate_tree_shap(train_result.model, X_test)

    df_shap_importance = mean_absolute_shap(shap_values, feature_cols)

    print("   => Hasil Analisis SHAP:")
    print(df_shap_importance)

    print("\nVerifikasi Tahap 3 Selesai! Explainable AI (SHAP) berhasil diterapkan dan membuktikan fitur mana yang paling penting.")

    print("\n=== MVG Tahap 4: Hyperparameter Tuning (RandomizedSearchCV + TimeSeriesSplit) ===")
    from src.modeling.tuning import tune_on_training_set

    # Hyperparameter tuning
    print("\n10. Menjalankan RandomizedSearchCV (3-fold TimeSeriesSplit) pada Data Latih...")
    base_estimator = create_estimator("xgboost", parameters={"random_state": 42})

    tuning_search = tune_on_training_set(base_estimator, "xgboost", X_train, y_train)
    print(f"   => Parameter Terbaik Ditemukan: {tuning_search.best_params_}")
    print(f"   => Skor CV Terbaik (Negative MAE): {tuning_search.best_score_:.4f}")

    tuned_predict_result = predict(tuning_search.best_estimator_, X_test)
    tuned_metrics = calculate_regression_metrics(y_test, tuned_predict_result.values)

    print("   => Metrik Model Hasil Tuning:")
    for metric_name, metric_value in tuned_metrics.items():
        print(f"      - {metric_name.upper()}: {metric_value:.4f}")

    print("\n   => Perbandingan dengan Model Default (Tahap 2):")
    for metric_name in metrics:
        diff = tuned_metrics[metric_name] - metrics[metric_name]
        sign = "+" if diff > 0 else ""
        print(f"      - {metric_name.upper()}: Default={metrics[metric_name]:.4f} -> Tuned={tuned_metrics[metric_name]:.4f} ({sign}{diff:.4f})")

    print("\nVerifikasi Tahap 4 Selesai! Hyperparameter Tuning berhasil diuji dan diverifikasi.")

    print("\n=== MVG Tahap 5: Perbandingan Algoritma (LightGBM) & Pengaruh Cuaca (Skenario 2) ===")

    # LightGBM (Scenario 1)
    print("\n12. Melatih dan Evaluasi Model LightGBM pada Skenario 1...")
    lgb_model_s1 = create_estimator("lightgbm", parameters={"random_state": 42, "verbose": -1})
    lgb_train_res_s1 = train_model(lgb_model_s1, X_train, y_train)
    lgb_pred_res_s1 = predict(lgb_train_res_s1.model, X_test)
    lgb_metrics_s1 = calculate_regression_metrics(y_test, lgb_pred_res_s1.values)

    print(f"   => Waktu Pelatihan LightGBM: {lgb_train_res_s1.training_time_seconds:.3f} detik")
    for k, v in lgb_metrics_s1.items():
        print(f"      - {k.upper()}: {v:.4f}")

    # Scenario 2 (pollutant + weather lags)
    print("\n13. Menyiapkan Fitur Skenario 2 (15 Fitur: 3 Lag Polutan + 12 Lag Cuaca)...")
    expected_s2 = resolve_scenario("carbon_monoxide", "scenario_2")
    df_s2 = create_lag_features(df_loc, pollutant="co", scenario="scenario_2", drop_incomplete_rows=True)

    train_s2, test_s2 = chronological_train_test_split(df_s2, test_fraction=0.2)
    s2_feature_cols = list(expected_s2.feature_names)

    X_train_s2 = train_s2[s2_feature_cols]
    y_train_s2 = train_s2[target_col]
    X_test_s2 = test_s2[s2_feature_cols]
    y_test_s2 = test_s2[target_col]

    print(f"   => Total fitur Skenario 2: {len(s2_feature_cols)} fitur")
    print(f"   => Daftar Fitur: {s2_feature_cols}")

    # Model training (Scenario 2)
    print("\n14. Melatih XGBoost & LightGBM pada Skenario 2...")
    xgb_s2 = create_estimator("xgboost", parameters={"random_state": 42})
    xgb_train_s2 = train_model(xgb_s2, X_train_s2, y_train_s2)
    xgb_pred_s2 = predict(xgb_train_s2.model, X_test_s2)
    xgb_metrics_s2 = calculate_regression_metrics(y_test_s2, xgb_pred_s2.values)

    lgb_s2 = create_estimator("lightgbm", parameters={"random_state": 42, "verbose": -1})
    lgb_train_s2 = train_model(lgb_s2, X_train_s2, y_train_s2)
    lgb_pred_s2 = predict(lgb_train_s2.model, X_test_s2)
    lgb_metrics_s2 = calculate_regression_metrics(y_test_s2, lgb_pred_s2.values)

    # SHAP analysis (Scenario 2)
    print("\n15. Menghitung SHAP Values Skenario 2 (Melihat Kontribusi Cuaca)...")
    shap_s2 = calculate_tree_shap(xgb_train_s2.model, X_test_s2)
    df_shap_s2 = mean_absolute_shap(shap_s2, s2_feature_cols)
    print("   => Top 7 Fitur Paling Berpengaruh di Skenario 2 (TreeSHAP):")
    print(df_shap_s2.head(7))

    # Evaluation summary
    print("\n" + "="*70)
    print(f"{'Kombinasi Eksperimen':<30} | {'MAE':<8} | {'RMSE':<8} | {'MAPE (%)':<8} | {'R2':<8} | {'Time (s)':<8}")
    print("="*70)
    print(f"{'XGBoost (Skenario 1 - Default)':<30} | {metrics['mae']:<8.2f} | {metrics['rmse']:<8.2f} | {metrics['mape']:<8.2f} | {metrics['r2']:<8.4f} | {train_result.training_time_seconds:<8.3f}")
    print(f"{'XGBoost (Skenario 1 - Tuned)':<30} | {tuned_metrics['mae']:<8.2f} | {tuned_metrics['rmse']:<8.2f} | {tuned_metrics['mape']:<8.2f} | {tuned_metrics['r2']:<8.4f} | {'-':<8}")
    print(f"{'LightGBM (Skenario 1)':<30} | {lgb_metrics_s1['mae']:<8.2f} | {lgb_metrics_s1['rmse']:<8.2f} | {lgb_metrics_s1['mape']:<8.2f} | {lgb_metrics_s1['r2']:<8.4f} | {lgb_train_res_s1.training_time_seconds:<8.3f}")
    print(f"{'XGBoost (Skenario 2 + Cuaca)':<30} | {xgb_metrics_s2['mae']:<8.2f} | {xgb_metrics_s2['rmse']:<8.2f} | {xgb_metrics_s2['mape']:<8.2f} | {xgb_metrics_s2['r2']:<8.4f} | {xgb_train_s2.training_time_seconds:<8.3f}")
    print(f"{'LightGBM (Skenario 2 + Cuaca)':<30} | {lgb_metrics_s2['mae']:<8.2f} | {lgb_metrics_s2['rmse']:<8.2f} | {lgb_metrics_s2['mape']:<8.2f} | {lgb_metrics_s2['r2']:<8.4f} | {lgb_train_s2.training_time_seconds:<8.3f}")
    print("="*70)
    print("\nVerifikasi Tahap 5 Selesai! Matriks perbandingan algoritma dan skenario fitur terverifikasi.")

if __name__ == "__main__":
    main()
