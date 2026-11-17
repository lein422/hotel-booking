# ШІ: Claude (Opus 5.5) – основна структура класу HotelController і фонові операції.
# Змінено: самостійно доповнено CRUD-методи, перевірку даних, обробку помилок, фільтрацію, сортування та скасування операцій.
import logging
import queue
import threading
from datetime import date, datetime
from typing import Any, Callable, NoReturn

from model.booking import Booking
from model.guest import Guest
from model.room import Room, ROOM_TYPE_NAMES
from service.hotel_service import HotelService, OperationCancelled

logger = logging.getLogger(__name__)

class HotelController:
    """Контролер для взаємодії між графічним інтерфейсом і сервісом готелю."""

    DATE_FORMAT = "%d.%m.%Y"

    def __init__(self, service: HotelService) -> None:
        """Ініціалізує сервіс, чергу повідомлень і фоновий потік."""
        self.__service = service
        self.__message_queue = queue.Queue()
        self.__worker: threading.Thread | None = None
        self.__cancel_event = threading.Event()
        self.__cancellable = False

    @staticmethod
    def __parse_date(value: str) -> date:
        """Перетворює рядок у дату."""
        try:
            return datetime.strptime(value, HotelController.DATE_FORMAT).date()
        except (ValueError, TypeError):
            raise ValueError("Дата має бути у форматі ДД.ММ.РРРР")

    @staticmethod
    def __parse_int(value: str, field_name: str) -> int:
        """Перетворює рядок у ціле число."""
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(f"{field_name} має бути цілим числом")

    @staticmethod
    def __parse_optional_int(value: str | None, field_name: str) -> int | None:
        """Повертає None для порожнього значення або перетворює його на число."""
        if value is None or not value.strip():
            return None
        return HotelController.__parse_int(value, field_name)

    @staticmethod
    def __parse_optional_date(value: str | None) -> date | None:
        """Повертає None для порожньої дати або перетворює її на дату."""
        if value is None or not value.strip():
            return None
        return HotelController.__parse_date(value)

    def __handle_os_error(self, error: OSError) -> NoReturn:
        """Обробляє помилки збереження даних."""
        logger.exception("Помилка під час збереження даних")
        raise ValueError("Не вдалося зберегти дані у файл") from error

    def __booking_to_row(self, booking: Booking) -> tuple:
        """Перетворює бронювання на рядок для таблиці."""
        return (
            str(booking.booking_id), booking.guest.full_name, booking.guest.phone,
            str(booking.room.number), booking.room.room_type, str(booking.guests_count),
            booking.check_in.strftime(self.DATE_FORMAT), booking.check_out.strftime(self.DATE_FORMAT),
            str(booking.nights), f"{booking.calculate_total():.2f}")

    def get_booking_rows(
        self, search_text: str = "", room_type: str | None = None,
        room_number: str | None = None, date_from: str | None = None,
        date_to: str | None = None, sort_key: str | None = None,
        reverse: bool = False
    ) -> list[tuple]:
        """Повертає відфільтровані та відсортовані бронювання для таблиці."""
        bookings = self.__service.search_bookings(search_text)
        filtered = self.__service.filter_bookings(
            room_type=room_type, date_from=self.__parse_optional_date(date_from),
            date_to=self.__parse_optional_date(date_to),
            room_number=self.__parse_optional_int(room_number, "Номер кімнати"))
        filtered_ids = {booking.booking_id for booking in filtered}
        bookings = [booking for booking in bookings if booking.booking_id in filtered_ids]
        if sort_key:
            bookings = self.__service.sort_bookings(bookings, sort_key, reverse)
        return [self.__booking_to_row(booking) for booking in bookings]

    def get_guest_rows(self, search_text: str = "") -> list[tuple]:
        """Повертає гостей для таблиці; якщо є текст – лише знайдених за ПІБ або телефоном."""
        guests = self.__service.search_guests(search_text)
        return [(guest.phone, guest.last_name, guest.first_name, guest.middle_name, guest.email)
                for guest in guests]

    @staticmethod
    def get_room_type_names() -> list[str]:
        """Назви типів номерів для випадних списків."""
        return list(ROOM_TYPE_NAMES.values())

    @staticmethod
    def __room_to_row(room: Room) -> tuple:
        """Перетворює номер на рядок для таблиці."""
        return (str(room.number), room.room_type, str(room.capacity), f"{room.price_per_night:.2f}")

    def get_room_rows(self, room_type: str | None = None,
                      check_in: str | None = None, check_out: str | None = None) -> list[tuple]:
        """Повертає номери для таблиці з фільтром за типом і вільними датами."""
        rooms = self.__service.filter_rooms(
            room_type, self.__parse_optional_date(check_in), self.__parse_optional_date(check_out))
        return [self.__room_to_row(room) for room in sorted(rooms, key=lambda r: r.number)]

    def get_room_row(self, number: str) -> tuple:
        """Повертає рядок номера за його номером."""
        for row in self.get_room_rows():
            if row[0] == number:
                return row
        raise ValueError(f"Номер {number} не знайдено.")

    @staticmethod
    def __parse_price(value: str) -> float:
        """Перетворює рядок у ціну, кома теж підходить."""
        try:
            return float(value.replace(",", "."))
        except (ValueError, AttributeError):
            raise ValueError("Ціна має бути числом")

    def add_room(self, room_type: str, number: str, capacity: str, price: str) -> Room:
        """Додає номер з даних форми."""
        try:
            return self.__service.add_room(
                room_type, self.__parse_int(number, "Номер кімнати"),
                self.__parse_int(capacity, "Місткість"), self.__parse_price(price))
        except OSError as error:
            self.__handle_os_error(error)

    def update_room(self, room_type: str, number: str, capacity: str, price: str) -> Room:
        """Оновлює номер з даних форми."""
        try:
            return self.__service.update_room(
                room_type, self.__parse_int(number, "Номер кімнати"),
                self.__parse_int(capacity, "Місткість"), self.__parse_price(price))
        except OSError as error:
            self.__handle_os_error(error)

    def delete_room(self, number: str) -> None:
        """Видаляє номер."""
        try:
            self.__service.delete_room(self.__parse_int(number, "Номер кімнати"))
        except OSError as error:
            self.__handle_os_error(error)

    def get_booking_row(self, booking_id: str) -> tuple:
        """Повертає рядок бронювання за його ID, а не з клітинок таблиці."""
        number = self.__parse_int(booking_id, "ID бронювання")
        for booking in self.__service.get_bookings():
            if booking.booking_id == number:
                return self.__booking_to_row(booking)
        raise ValueError(f"Бронювання №{booking_id} не знайдено.")

    def get_guest_row(self, phone: str) -> tuple:
        """Повертає рядок гостя за телефоном."""
        for row in self.get_guest_rows():
            if row[0] == phone:
                return row
        raise ValueError(f"Гостя з телефоном {phone} не знайдено.")

    def is_busy(self) -> bool:
        """Показує, чи працює зараз фонова задача."""
        return self.__worker is not None and self.__worker.is_alive()

    def get_room_options(self) -> list[tuple]:
        """Повертає список номерів для випадного списку."""
        rooms = self.__service.get_rooms()
        return [(room.number, f"{room.number} – {room.room_type}, місткість: {room.capacity}") for room in rooms]

    def create_booking(
        self, guest_phone: str, room_number: str,
        guests_count: str, check_in: str, check_out: str
    ) -> Booking:
        """Створює бронювання на основі даних форми."""
        try:
            return self.__service.create_booking(
                guest_phone, self.__parse_int(room_number, "Номер кімнати"),
                self.__parse_int(guests_count, "Кількість гостей"),
                self.__parse_date(check_in), self.__parse_date(check_out))
        except OSError as error:
            self.__handle_os_error(error)

    def update_booking(
        self, booking_id: str, guest_phone: str, room_number: str,
        guests_count: str, check_in: str, check_out: str
    ) -> Booking:
        """Оновлює дані бронювання."""
        try:
            return self.__service.update_booking(
                self.__parse_int(booking_id, "ID бронювання"), guest_phone,
                self.__parse_int(room_number, "Номер кімнати"),
                self.__parse_int(guests_count, "Кількість гостей"),
                self.__parse_date(check_in), self.__parse_date(check_out))
        except OSError as error:
            self.__handle_os_error(error)

    def cancel_booking(self, booking_id: str) -> None:
        """Скасовує бронювання за його ідентифікатором."""
        try:
            self.__service.cancel_booking(self.__parse_int(booking_id, "ID бронювання"))
        except OSError as error:
            self.__handle_os_error(error)

    def add_guest(self, phone: str, last_name: str, first_name: str, middle_name: str, email: str) -> Guest:
        """Додає нового гостя."""
        try:
            return self.__service.add_guest(
                phone=phone, last_name=last_name, first_name=first_name,
                middle_name=middle_name, email=email)
        except OSError as error:
            self.__handle_os_error(error)

    def update_guest(self, phone: str, last_name: str, first_name: str, middle_name: str, email: str) -> Guest:
        """Оновлює дані гостя."""
        try:
            return self.__service.update_guest(
                phone=phone, last_name=last_name, first_name=first_name,
                middle_name=middle_name, email=email)
        except OSError as error:
            self.__handle_os_error(error)

    def delete_guest(self, phone: str) -> None:
        """Видаляє гостя за номером телефону."""
        try:
            self.__service.delete_guest(phone)
        except OSError as error:
            self.__handle_os_error(error)

    def __start_task(self, task_name: str, function: Callable, *args: Any, cancellable: bool = False) -> None:
        """Запускає фонову задачу, якщо інша задача ще не виконується."""
        if self.is_busy():
            raise ValueError("Зачекайте завершення поточної операції")
        self.__cancel_event.clear()
        self.__cancellable = cancellable
        self.__worker = threading.Thread(
            target=self.__run_task, args=(task_name, function, args), daemon=True)
        self.__worker.start()

    def __run_task(self, task_name: str, function: Callable, args: tuple) -> None:
        """Виконує фонову задачу та передає результати через чергу."""
        self.__message_queue.put(("start", task_name))
        try:
            result = function(*args)
            message = str(result) if result is not None else "Операцію успішно завершено"
            self.__message_queue.put(("done", message))
        except OperationCancelled:
            logger.info("Операцію скасовано: %s", task_name)
            self.__message_queue.put(("cancelled", f"{task_name}: скасовано, дані не змінено"))
        except Exception as error:
            logger.exception("Помилка під час виконання операції: %s", task_name)
            self.__message_queue.put(("error", str(error)))

    def can_cancel(self) -> bool:
        """Показує, чи можна скасувати поточну задачу."""
        return self.is_busy() and self.__cancellable

    def cancel_task(self) -> None:
        """Просить фоновий потік зупинитися. Потік перевіряє прапорець сам."""
        if self.can_cancel():
            self.__cancel_event.set()

    def start_import(self, path: str) -> None:
        """Запускає імпорт даних у фоновому потоці. Імпорт можна скасувати."""
        self.__start_task(
            "Імпорт JSON", self.__service.import_from_file, path, self.__cancel_event, cancellable=True)

    def start_export_xml(self, path: str, start_date: str, end_date: str) -> None:
        """Запускає створення XML-звіту у фоновому потоці."""
        start = self.__parse_date(start_date)
        end = self.__parse_date(end_date)
        if end <= start:
            raise ValueError("Кінцева дата має бути пізніше початкової.")
        self.__start_task(
            "Звіт XML", self.__service.export_occupancy_report,
            path, start, end)

    def start_export_json(self, path: str) -> None:
        """Запускає експорт даних у фоновому потоці."""
        self.__start_task("Експорт JSON", self.__service.export_to_file, path)

    def poll_messages(self) -> list[tuple]:
        """Отримує всі доступні повідомлення з черги."""
        messages = []
        while True:
            try:
                messages.append(self.__message_queue.get_nowait())
            except queue.Empty:
                break
        return messages