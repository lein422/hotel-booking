import json
import logging
import os
import threading
from pathlib import Path

from model.booking import Booking
from model.guest import Guest
from model.room import Room, room_from_dict

logger = logging.getLogger(__name__)

class HotelRepository:
    """Читає та записує дані готелю у файл JSON."""

    def __init__(self, file_path: Path):
        self.__file_path = Path(file_path)
        self.__lock = threading.Lock()

    def load(
            self,
            path: Path | None = None
    ) -> tuple[dict[int, Room], dict[str, Guest], dict[int, Booking]]:
        """Завантажує номери, гостей і бронювання з файлу."""

        file_path = Path(path) if path is not None else self.__file_path

        with self.__lock:
            if not file_path.exists():
                logger.warning("Файл %s не знайдено.", file_path)
                return {}, {}, {}

            try:
                with file_path.open("r", encoding="utf-8") as file:
                    data = json.load(file)

            except json.JSONDecodeError as error:
                logger.exception("Помилка читання JSON-файлу %s", file_path)
                raise ValueError(f"Помилка читання JSON-файлу: {error}") from error

            except OSError:
                logger.exception("Помилка читання файлу %s", file_path)
                raise

            if not isinstance(data, dict):
                raise ValueError("Некоректна структура файлу: корінь має бути словником.")

            for key in ("rooms", "guests", "bookings"):
                if key not in data or not isinstance(data[key], list):
                    raise ValueError(f"Некоректна структура файлу: відсутній список {key}.")

            rooms = {}

            for item in data["rooms"]:
                room = room_from_dict(item)

                if room.number in rooms:
                    raise ValueError(f"Дублікат номера кімнати: {room.number}")

                rooms[room.number] = room

            guests = {}

            for item in data["guests"]:
                guest = Guest.from_dict(item)
                if guest.phone in guests:
                    raise ValueError(f"Дублікат телефону гостя: {guest.phone}")

                guests[guest.phone] = guest

            bookings = {}

            for item in data["bookings"]:
                booking = Booking.from_dict(item, guests, rooms)
                if booking.booking_id in bookings:
                    raise ValueError(f"Дублікат бронювання: {booking.booking_id}")

                bookings[booking.booking_id] = booking

            return rooms, guests, bookings

    def save(self, rooms: dict, guests: dict, bookings: dict) -> None:
        """Зберігає всі дані у файл через тимчасовий файл."""

        data = {
            "rooms": [room.to_dict() for room in rooms.values()],
            "guests": [guest.to_dict() for guest in guests.values()],
            "bookings": [booking.to_dict() for booking in bookings.values()]
        }

        temp_path = self.__file_path.with_suffix(".tmp")
        with self.__lock:
            try:
                self.__file_path.parent.mkdir(parents=True, exist_ok=True)

                with temp_path.open("w", encoding="utf-8") as file:
                    json.dump(data, file, ensure_ascii=False, indent=4)
                os.replace(temp_path, self.__file_path)

            except OSError:
                logger.exception("Помилка збереження файлу %s", self.__file_path)
                temp_path.unlink(missing_ok=True)
                raise