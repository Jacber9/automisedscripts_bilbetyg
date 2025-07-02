import os
import requests
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Ladda miljövariabler från .env
load_dotenv()

# Miljövariabler
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CAR_API_URL = "https://api.car.info/v3/app/oozmarketing/classifieds"
API_IDENTIFIER = os.getenv("CAR_API_IDENTIFIER")
API_KEY = os.getenv("CAR_API_KEY")

# Initiera Supabase-klient
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Hjälpfunktioner
def to_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

def to_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return None

def to_timestamp(val):
    if not val:
        return None
    if isinstance(val, str) and len(val) == 10:
        return val + "T00:00:00.000Z"
    try:
        return datetime.fromisoformat(val).isoformat()
    except Exception:
        return None

def log_api_response(data):
    try:
        res = supabase.table("ads_api_log").insert({"response": data}).execute()
        # Förväntar sig att res.data är en lista med den nya raden
        if hasattr(res, "data") and res.data and isinstance(res.data, list):
            return res.data[0]["id"]  # Hämta id på nya raden
        elif hasattr(res, "data") and not res.data:
            print("⚠️ Inget loggat i ads_api_log:", res)
    except Exception as e:
        print("EXCEPTION vid loggning:", e)
    return None

def main():
    total_errors = 0
    total_cars = 0
    batch_count = 0

    while True:
        batch_count += 1
        print(f"🔍 Hämtar batch {batch_count} från bil-API...")

        try:
            response = requests.get(CAR_API_URL, headers={
                "x-auth-identifier": API_IDENTIFIER,
                "x-auth-key": API_KEY,
                "Accept": "application/json"
            })
            api_data = response.json()
            api_log_id = log_api_response(api_data)  # <-- Få log-id:t här
        except Exception as e:
            print("❌ API FEL:", e)
            break

        if not api_data or "result" not in api_data:
            print("⚠️ API-data saknas eller har ingen 'result'.")
            break

        for car in api_data["result"]:
            total_cars += 1
            mapped = {
                "carinfo_id": to_int(car.get("id")),
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
                "image_urls": car.get("images", []),   # <-- Spara hela arrayen här!
                "ads_api_log_id": api_log_id           # <-- Spara logg-id här!
            }

            try:
                upsert = supabase.table("ads_cars").upsert(mapped, on_conflict=["carinfo_id"]).execute()
                if hasattr(upsert, "data") and not upsert.data:
                    total_errors += 1
                    print("❌ Upsert error:", upsert)
            except Exception as e:
                total_errors += 1
                print("EXCEPTION vid upsert i ads_cars:", e)
                continue

        if not api_data.get("have_more"):
            print("✅ Inga fler batchar att hämta.")
            break

    print(f"✅ Import klar. {total_cars} bilar bearbetade. {total_errors} fel.")

if __name__ == "__main__":
    main()
