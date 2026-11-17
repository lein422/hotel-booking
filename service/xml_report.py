import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

class OccupancyReport:
    """Формує XML-звіт про завантаженість номерів готелю."""

    @staticmethod
    def save(rooms: list, bookings: list, start_date: date,
             end_date: date, file_path: str | Path) -> None:
        """Створює XML-звіт за вказаний період."""
        if end_date <= start_date:
            raise ValueError("Кінцева дата має бути пізніше початкової.")

        root = ET.Element("occupancy_report")
        root.set("start_date", start_date.isoformat())
        root.set("end_date", end_date.isoformat())
        total_nights = (end_date - start_date).days

        for room in rooms:
            occupied_nights = 0
            income = 0.0

            for booking in bookings:
                if booking.room.number != room.number:
                    continue

                overlap_start = max(start_date, booking.check_in)
                overlap_end = min(end_date, booking.check_out)
                nights = (overlap_end - overlap_start).days

                if nights > 0:
                    occupied_nights += nights
                    income += booking.calculate_total() * nights / booking.nights

            room_element = ET.SubElement(root, "room")
            ET.SubElement(room_element, "number").text = str(room.number)
            ET.SubElement(room_element, "type").text = room.room_type
            ET.SubElement(room_element, "occupied_nights").text = str(occupied_nights)
            ET.SubElement(room_element, "occupancy_percent").text = (
                f"{occupied_nights / total_nights * 100:.2f}")
            ET.SubElement(room_element, "income").text = f"{income:.2f}"

        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(path, encoding="utf-8", xml_declaration=True)