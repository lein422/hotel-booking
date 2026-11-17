import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from service.repository import HotelRepository
from service.overlap_checker import OverlapChecker
from service.hotel_service import HotelService
from controller.hotel_controller import HotelController
from view.main_window import MainWindow

def main():
    base_path = Path(__file__).resolve().parent
    data_path = base_path / "data" / "hotel.json"
    log_path = base_path / "logs" / "hotel.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        handlers=[logging.FileHandler(log_path, encoding="utf-8"), logging.StreamHandler()])

    logger = logging.getLogger(__name__)
    logger.info("Застосунок запущено")

    root = tk.Tk()
    root.withdraw()
    repository = HotelRepository(data_path)
    overlap_checker = OverlapChecker()

    try:
        service = HotelService(repository, overlap_checker)
        controller = HotelController(service)
        MainWindow(root, controller)
    except (ValueError, OSError) as error:
        logger.exception("Помилка під час завантаження даних")
        messagebox.showerror("Помилка завантаження", f"Не вдалося завантажити дані готелю.\n\nПричина: {error}")
        root.destroy()
        return

    def report_callback_exception(exc_type, exc_value, exc_traceback):
        logger.error("Сталася непередбачена помилка", exc_info=(exc_type, exc_value, exc_traceback))
        messagebox.showerror("Помилка", "Сталася непередбачена помилка. Деталі записано в журнал.")

    root.report_callback_exception = report_callback_exception
    root.deiconify()
    root.mainloop()
    logger.info("Застосунок закрито")

if __name__ == "__main__":
    main()
