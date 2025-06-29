import os
import requests
import time
from supabase import create_client, Client
from dotenv import load_dotenv

# ☡️ Ladda miljövariabler
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CAR_API_KEY = os.getenv("CAR_API_KEY")
CAR_API_IDENTIFIER = os.getenv("CAR_API_IDENTIFIER")

if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, CAR_API_KEY, CAR_API_IDENTIFIER]):
    raise ValueError("❌ Någon av miljövariablerna saknas. Kontrollera din .env-fil.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def to_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return None

def to_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return None

def to_timestamp(val):
    return val if val else None

def fetch_updated_ads(carinfo_ids):
    url = "https://api.car.info/v3/app/oozmarketing/classifieds"
    headers = {
        "x-auth-identifier": CAR_API_IDENTIFIER,
        "x-auth-key": CAR_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=carinfo_ids)
    if response.status_code == 200:
        result = response.json().get("result", [])
        return result if isinstance(result, list) else []
    else:
        print(f"❌ Fel vid POST-anrop: {response.status_code} - {response.text}")
        return []

def update_database_with_post_response(data):
    for car in data:
        carinfo_id = to_int(car.get("id"))
        if not carinfo_id:
            continue

        update_data = {
            "carinfo_id": carinfo_id,
            "licence_plate": car.get("licence_plate"),
            "vin": car.get("vin"),
            "engine_name": car.get("engine_name"),
            "engine_code": car.get("engine_code"),
            "engine_type": car.get("engine_type"),
            "price": to_int(car.get("price")),
            "prices": car.get("prices") if isinstance(car.get("prices"), list) else None,
            "odometer_km": to_int(car.get("odometer_km")),
            "dates_published": to_timestamp(car.get("dates", {}).get("published")),
            "dates_removed": to_timestamp(car.get("dates", {}).get("removed")),
            "dates_changed": to_timestamp(car.get("dates", {}).get("changed")),
            "dates_sold": to_timestamp(car.get("dates", {}).get("sold")),
            "days_for_sale": to_int(car.get("days_for_sale")),
            "status": car.get("status"),
            "brand": car.get("brand"),
            "model": car.get("model"),
            "series": car.get("series"),
            "generation": car.get("generation"),
            "chassis": car.get("chassis"),
            "model_year": to_int(car.get("model_year")),
            "name": car.get("name"),
            "transmission_type": car.get("transmission_type"),
            "color": car.get("color"),
            "url": car.get("url"),
            "source": car.get("source"),
            "trim_packages": car.get("trim_packages") or [],
            "fuels": car.get("fuels") or [],
            "accelleration_0_to_100_kmh": to_float(car.get("accelleration_0_to_100_kmh")),
            "awards": car.get("awards"),
            "power_kw": to_float(car.get("power_kW")),
            "horsepower_hp": to_float(car.get("horsepower_hp")),
            "number_of_doors": to_int(car.get("number_of_doors")),
            "electric_engine": car.get("electric_engine"),
            "type_of_electric_car": car.get("type_of_electric_car"),
            "sales_name": car.get("sales_name"),
            "wltp_fuel_consumption_combined_min": to_float(car.get("wltp", {}).get("fuel_consumption_combined", {}).get("min")),
            "wltp_fuel_consumption_combined_max": to_float(car.get("wltp", {}).get("fuel_consumption_combined", {}).get("max")),
            "wltp_co2_emission_combined_min": to_float(car.get("wltp", {}).get("CO2_emission_combined", {}).get("min")),
            "wltp_co2_emission_combined_max": to_float(car.get("wltp", {}).get("CO2_emission_combined", {}).get("max")),
            "nedc_fuel_consumption_combined_min": to_float(car.get("nedc", {}).get("fuel_consumption_combined", {}).get("min")),
            "nedc_fuel_consumption_combined_max": to_float(car.get("nedc", {}).get("fuel_consumption_combined", {}).get("max")),
            "nedc_co2_emission_combined_min": to_float(car.get("nedc", {}).get("CO2_emission_combined", {}).get("min")),
            "nedc_co2_emission_combined_max": to_float(car.get("nedc", {}).get("CO2_emission_combined", {}).get("max")),
            "euro_ncap_year": to_int(car.get("euro_ncap", {}).get("year")),
            "euro_ncap_result": to_int(car.get("euro_ncap", {}).get("result")),
            "image_urls": car.get("images", [])
        }

        try:
            supabase.table("ads_cars").update(update_data).eq("carinfo_id", carinfo_id).execute()
            print(f"✅ Uppdaterade bil med carinfo_id {carinfo_id}")
        except Exception as e:
            print(f"❌ Misslyckades att uppdatera bil {carinfo_id}: {e}")

# 🚀 Huvudloop: bläddra igenom alla bilar i databasen i steg om 1000
if __name__ == "__main__":
    batch_size = 1000
    offset = 0
    batch_index = 1

    while True:
        print(f"\n📥 Hämtar carinfo_id batch {batch_index} (OFFSET {offset})...")

        response = supabase.table("ads_cars") \
            .select("carinfo_id") \
            .order("carinfo_id") \
            .range(offset, offset + batch_size - 1) \
            .execute()

        rows = response.data or []
        if not rows:
            print("✅ Alla annonser har uppdaterats!")
            break

        carinfo_ids = [row["carinfo_id"] for row in rows if row.get("carinfo_id")]

        print(f"🚗 Batch {batch_index} innehåller {len(carinfo_ids)} annonser – skickar till API...")
        data = fetch_updated_ads(carinfo_ids)
        update_database_with_post_response(data)

        offset += batch_size
        batch_index += 1
        time.sleep(1)  # undvik överbelastning

    print("✅ Klart! Alla poster har bearbetats.")
