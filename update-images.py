import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Ladda miljövariabler från .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CAR_API_IDENTIFIER = os.getenv("CAR_API_IDENTIFIER")
CAR_API_KEY = os.getenv("CAR_API_KEY")

API_URL = "https://api.car.info/v3/app/oozmarketing/classifieds"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def fetch_missing_image_cars(batch_size=1000, offset=0):
    # Hämtar bilar där image_urls är NULL, tom lista eller tom sträng
    response = supabase.table("ads_cars") \
        .select("carinfo_id, image_urls") \
        .order("carinfo_id") \
        .range(offset, offset + batch_size - 1) \
        .execute()
    rows = response.data or []

    # Filtrera till bara de rader som verkligen saknar bilder (NULL, [], "")
    filtered = []
    for row in rows:
        image_urls = row.get("image_urls")
        if (
            image_urls is None
            or image_urls == []
            or image_urls == ""
        ):
            filtered.append(row)
    return filtered

def update_image_urls(api_result, supabase):
    updated = 0
    for car in api_result.get("result", []):
        carinfo_id = car.get("id")
        images = car.get("images", [])
        if carinfo_id and images:
            try:
                supabase.table("ads_cars").update({"image_urls": images}).eq("carinfo_id", carinfo_id).execute()
                updated += 1
            except Exception as e:
                print(f"🚨 Fel vid uppdatering av carinfo_id {carinfo_id}: {e}")
    print(f"✅ {updated} annonser uppdaterade med nya bilder")

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

    while True:
        print(f"\n📥 Hämtar batch {batch_index} (OFFSET {offset}) från ads_cars...")
        cars = fetch_missing_image_cars(batch_size, offset)
        print(f"🔢 Antal bilar utan bilder i denna batch: {len(cars)}")
        if not cars:
            print("✅ Alla bilar utan bilder har bearbetats!")
            break

        carinfo_ids = [car["carinfo_id"] for car in cars if car.get("carinfo_id")]
        if carinfo_ids:
            try:
                print(f"➡️ Skickar {len(carinfo_ids)} carinfo_id till API...")
                api_response = requests.post(
                    API_URL,
                    json=carinfo_ids,  # Ren array, inte objekt!
                    headers=headers,
                    timeout=90
                )
                print(f"API-svar: {api_response.status_code} {api_response.text[:200]}...")
                if api_response.ok:
                    api_data = api_response.json()
                    update_image_urls(api_data, supabase)
                else:
                    print(f"🚨 Fel från API: {api_response.status_code} {api_response.text}")
            except Exception as e:
                print(f"🚨 Fel vid API-anrop: {e}")

        offset += batch_size
        batch_index += 1
        time.sleep(1)

    print("🎉 Klar!")

if __name__ == "__main__":
    main()
