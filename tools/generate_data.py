import json
import random
from datetime import date, timedelta
from pathlib import Path

BASE_PATH = Path(__file__).resolve().parent.parent
SOURCE_PATH = BASE_PATH / "data" / "hotel.json"
OUTPUT_PATH = BASE_PATH / "data" / "hotel_test.json"
BOOKING_COUNT = 100000

def generate_data(count: int = BOOKING_COUNT) -> None:
    """Створює тестові бронювання без перетину дат."""
    with SOURCE_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    rooms = data["rooms"]
    guests = data["guests"]
    bookings = []
    next_dates = {room["number"]: date(2026, 1, 1) for room in rooms}

    for booking_id in range(1, count + 1):
        room = rooms[(booking_id - 1) % len(rooms)]
        guest = random.choice(guests)
        check_in = next_dates[room["number"]]
        nights = random.randint(1, 7)
        check_out = check_in + timedelta(days=nights)

        bookings.append({
            "id": booking_id,
            "guest_phone": guest["phone"],
            "room_number": room["number"],
            "guests_count": random.randint(1, room["capacity"]),
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat()
        })

        next_dates[room["number"]] = check_out + timedelta(
            days=random.randint(1, 3))

    data["bookings"] = bookings

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

    print(f"Створено {count} бронювань: {OUTPUT_PATH}")

if __name__ == "__main__":
    generate_data()