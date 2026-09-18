import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry

# ======================================================
# Setup
# ======================================================

cache_session = requests_cache.CachedSession(
    ".cache",
    expire_after=-1
)

retry_session = retry(
    cache_session,
    retries=5,
    backoff_factor=0.2
)

openmeteo = openmeteo_requests.Client(session=retry_session)

# ======================================================
# Parameter
# ======================================================

START_DATE = "2024-10-26"
END_DATE = "2026-08-04"

locations = [
    # Jakarta
    ("Taman Kamal", -6.100000, 106.700000),
    ("Pelabuhan Muara Baru", -6.100000, 106.800000),
    ("Daerah Pelabuhan Tanjung Priuk", -6.100000, 106.900000),
    ("Petamburan Daerah perkantoran dan Transjakarta", -6.200000, 106.800000),
    ("SMP Negeri 92 Jakarta Timur", -6.200000, 106.900000),
    ("Perumahan dekat Tol Depok-Antasari", -6.300000, 106.800000),
    ("TMII", -6.300000, 106.900000),

    # Tangerang
    ("Metland Cyberpuri", -6.200000, 106.700000),
    ("Tol Serpong (Interchange)", -6.300000, 106.700000),

    # Depok
    ("Pancoran Mas", -6.400000, 106.800000),
    ("Jl. Tol Jagorawi", -6.400000, 106.900000),

    # Bekasi
    ("Pantai Makmur", -6.100000, 107.000000),
    ("Kaliabang Tengah", -6.200000, 107.000000),
    ("Mustikasari", -6.300000, 107.000000),

    # Bogor
    ("Cibinong", -6.400000, 106.700000)
]

weather_url = "https://archive-api.open-meteo.com/v1/archive"

air_url = "https://air-quality-api.open-meteo.com/v1/air-quality"

CO_data = []
CO2_data = []

# ======================================================
# Download
# ======================================================

for name, lat, lon in locations:

    print(f"Downloading {name}...")

    # ===========================
    # WEATHER
    # ===========================

    weather_params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "rain",
            "wind_speed_100m"
        ],
        "timezone": "Asia/Bangkok"
    }

    weather_response = openmeteo.weather_api(
        weather_url,
        params=weather_params
    )[0]

    weather_hourly = weather_response.Hourly()

    weather_df = pd.DataFrame({

        "datetime": pd.date_range(

            start=pd.to_datetime(
                weather_hourly.Time(),
                unit="s",
                utc=True
            ),

            end=pd.to_datetime(
                weather_hourly.TimeEnd(),
                unit="s",
                utc=True
            ),

            freq=pd.Timedelta(
                seconds=weather_hourly.Interval()
            ),

            inclusive="left"

        ).tz_convert("Asia/Bangkok"),

        "temperature_2m":
            weather_hourly.Variables(0).ValuesAsNumpy(),

        "relative_humidity_2m":
            weather_hourly.Variables(1).ValuesAsNumpy(),

        "rain":
            weather_hourly.Variables(2).ValuesAsNumpy(),

        "wind_speed_100m":
            weather_hourly.Variables(3).ValuesAsNumpy(),
    })

    # ===========================
    # AIR QUALITY
    # ===========================

    co_params = {

        "latitude": lat,
        "longitude": lon,

        "hourly": [
            "carbon_monoxide"
        ],

        "domains": "cams_global",

        "start_date": START_DATE,
        "end_date": END_DATE,

        "timezone": "Asia/Bangkok"

    }

    co_response = openmeteo.weather_api(
        air_url,
        params=co_params
    )[0]

    co_hourly = co_response.Hourly()

    co_df = pd.DataFrame({

        "datetime": pd.date_range(

            start=pd.to_datetime(
                co_hourly.Time(),
                unit="s",
                utc=True
            ),

            end=pd.to_datetime(
                co_hourly.TimeEnd(),
                unit="s",
                utc=True
            ),

            freq=pd.Timedelta(
                seconds=co_hourly.Interval()
            ),

            inclusive="left"

        ),

        "carbon_monoxide":
            co_hourly.Variables(0).ValuesAsNumpy(),

    })

    co2_params = {
    
            "latitude": lat,
            "longitude": lon,
    
            "hourly": [
                "carbon_dioxide"
            ],
    
            "domains": "cams_global",
    
            "start_date": START_DATE,
            "end_date": END_DATE,
    
            "timezone": "Asia/Bangkok"
    
        }
    
    co2_response = openmeteo.weather_api(
            air_url,
            params=co2_params
    )[0]
    
    co2_hourly = co2_response.Hourly()
    
    co2_df = pd.DataFrame({
    
        "datetime": pd.date_range(

            start=pd.to_datetime(
                co2_hourly.Time(),
                unit="s",
                utc=True
            ),

            end=pd.to_datetime(
                co2_hourly.TimeEnd(),
                unit="s",
                utc=True
            ),

            freq=pd.Timedelta(
                seconds=co2_hourly.Interval()
            ),

            inclusive="left"

        ),

        "carbon_dioxide":
            co2_hourly.Variables(0).ValuesAsNumpy(),

    })

    # ===========================
    # Merge
    # ===========================

    df_co = pd.merge(

        weather_df,
        co_df,

        on="datetime",

        how="inner"

    )

    df_co2 = pd.merge(
        weather_df,
        co2_df,

        on="datetime",
        how="inner"
    )

    df_co["location"] = name
    df_co["latitude"] = lat
    df_co["longitude"] = lon

    df_co2["location"] = name
    df_co2["latitude"] = lat
    df_co2["longitude"] = lon

    CO_data.append(df_co)
    CO2_data.append(df_co2)

# ======================================================
# Final Dataset
# ======================================================

co_final_df = pd.concat(
    CO_data,
    ignore_index=True
)

co2_final_df = pd.concat(
    CO2_data,
    ignore_index=True
)

cols_co = [

    "location",
    "latitude",
    "longitude",
    "datetime",

    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_100m",

    "carbon_monoxide"

]

cols_co2 = [

    "location",
    "latitude",
    "longitude",
    "datetime",

    "temperature_2m",
    "relative_humidity_2m",
    "rain",
    "wind_speed_100m",

    "carbon_dioxide",

]

co_final_df = co_final_df[cols_co]
co2_final_df = co2_final_df[cols_co2]


start_datetime = pd.Timestamp(
    "2024-10-26 07:00:00",
    tz="Asia/Bangkok"
)

co_final_df = co_final_df[co_final_df["datetime"] >= start_datetime].reset_index(drop=True)
co2_final_df = co2_final_df[co2_final_df["datetime"] >= start_datetime].reset_index(drop=True)

print(co_final_df.head())
print(co2_final_df.head())


co_final_df.to_csv(
    "jakarta_co_weather_dataset.csv",
    index=False
)

co2_final_df.to_csv(
    "jakarta_co2_weather_dataset.csv",
    index=False
)

print("\nDone!")
print(co_final_df.shape)
print(co2_final_df.shape)