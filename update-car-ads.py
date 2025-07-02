import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CAR_API_IDENTIFIER = os.getenv("CAR_API_IDENTIFIER")
CAR_API_KEY = os.getenv("CAR_API_KEY")
API_URL = "https://api.car.info/v3/app/oozmarketing/classifieds"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def to_int(x):
    try:
        return int(x)
    except:
        return None

def to_float(x):
    try:
        return float(x)
    except:
        return None

def to_timestamp(x):
    # Anpassa till ditt tidsformat om du vill hantera datumfält!
    return x

def fetch_all_cars_batch(batch_size=1000, offset=0):
    query = supabase.table("ads_cars").select("carinfo_id").order("carinfo_id").range(offset, offset + batch_size - 1)
    response = query.execute()
    return [row["carinfo_id"] for row in (response.data or []) if row.get("carinfo_id")]

def update_database_with_post_response(data):
    batch_log = []
    for car in data:
        carinfo_id = to_int(car.get("id"))
        if not carinfo_id:
            batch_log.append(f"⚠️ Saknar eller ogiltigt id på en bil: {car.get('id')}")
            continue

        response = supabase.table("ads_cars").select("*").eq("carinfo_id", carinfo_id).single().execute()
        if not response.data:
            batch_log.append(f"⚠️ Hittar ingen bil med carinfo_id {carinfo_id} i databasen.")
            continue

        current_row = response.data
        update_data = {}
        candidate_data = {
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
        for key, value in candidate_data.items():
            if value != current_row.get(key):
                update_data[key] = value

        if update_data:
            try:
                supabase.table("ads_cars").update(update_data).eq("carinfo_id", carinfo_id).execute()
                batch_log.append(f"✅ Bil {carinfo_id}: uppdaterade {list(update_data.keys())}")
            except Exception as e:
                batch_log.append(f"❌ Misslyckades att uppdatera bil {carinfo_id}: {e}")
        else:
            batch_log.append(f"➖ Bil {carinfo_id}: inga ändringar (ingen update behövs)")
    return batch_log

def main():
    batch_size = 1000
    offset = 0
    batch_index = 1

    headers = {
        "x-auth-identifier": CAR_API_IDENTIFIER,
        "x-auth-key": CAR_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Räkna antal bilar
    total_cars = supabase.table("ads_cars").select("carinfo_id", count="exact").execute().count
    print(f"\n🔎 Hittar totalt {total_cars} bilar i databasen.")

    while True:
        carinfo_ids = fetch_all_cars_batch(batch_size, offset)
        if not carinfo_ids:
            print("✅ Alla batcher har körts.")
            break

        print(f"\n📦 Batch {batch_index} | OFFSET {offset} | {len(carinfo_ids)} id skickas till API.")
        try:
            api_response = requests.post(
                API_URL,
                json=[int(cid) for cid in carinfo_ids],
                headers=headers,
                timeout=90
            )
            print(f"API-svar: {api_response.status_code}")
            if api_response.ok:
                data = api_response.json().get("result", [])
                batch_log = update_database_with_post_response(data)
                print(f"\n📝 Batch {batch_index} resultat:")
                for log in batch_log:
                    print(log)
            else:
                print(f"🚨 Fel från API: {api_response.status_code} {api_response.text}")
        except Exception as e:
            print(f"🚨 Fel vid API-anrop: {e}")

        offset += batch_size
        batch_index += 1
        time.sleep(1)

    print("🎉 KLAR!")

if __name__ == "__main__":
    main()
