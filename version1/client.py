import tkinter as tk
from tkinter import ttk, messagebox
import requests
import json
from datetime import datetime


class FinanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Финансовый анализатор")
        self.root.geometry("800x600")

        # Настройки соединения с сервером
        self.server_url = "http://localhost:5000"

        # Данные для выпадающих списков
        self.asset_types = ["Акции", "Криптовалюта", "Валюта"]
        self.assets = {
            "Акции": ["AAPL", "GOOGL", "MSFT"],
            "Криптовалюта": ["BTC-USD", "ETH-USD"],
            "Валюта": ["EUR-USD", "RUB-USD"]
        }

        # Создаем интерфейс
        self.create_widgets()

    def create_widgets(self):
        # Фрейм для элементов управления
        control_frame = tk.Frame(self.root)
        control_frame.pack(pady=10)

        # Выбор типа актива
        tk.Label(control_frame, text="Тип актива:").grid(row=0, column=0)
        self.asset_type = ttk.Combobox(control_frame, values=self.asset_types)
        self.asset_type.grid(row=0, column=1)
        self.asset_type.current(0)
        self.asset_type.bind("<<ComboboxSelected>>", self.update_assets)

        # Выбор конкретного актива
        tk.Label(control_frame, text="Актив:").grid(row=1, column=0)
        self.asset = ttk.Combobox(control_frame)
        self.asset.grid(row=1, column=1)
        self.update_assets()

        # Кнопка получения данных
        self.get_btn = tk.Button(control_frame, text="Получить данные", command=self.get_data)
        self.get_btn.grid(row=2, columnspan=2, pady=10)

        # Текстовая область для вывода данных
        self.output = tk.Text(self.root, height=20, width=90)
        self.output.pack(pady=10)

        # Кнопка очистки
        self.clear_btn = tk.Button(self.root, text="Очистить", command=self.clear_output)
        self.clear_btn.pack()

    def update_assets(self, event=None):
        """Обновляет список активов при изменении типа"""
        selected_type = self.asset_type.get()
        self.asset['values'] = self.assets.get(selected_type, [])
        if self.asset['values']:
            self.asset.current(0)

    def get_data(self):
        """Получает данные с сервера"""
        asset_type = self.asset_type.get()
        asset = self.asset.get()

        if not asset:
            messagebox.showerror("Ошибка", "Выберите актив!")
            return

        try:
            # Делаем запрос к серверу
            params = {
                "asset_type": asset_type,
                "asset": asset
            }

            response = requests.get(f"{self.server_url}/get_data", params=params)

            if response.status_code == 200:
                data = response.json()
                self.show_data(data)
            else:
                messagebox.showerror("Ошибка", f"Сервер вернул ошибку: {response.text}")

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось подключиться к серверу: {str(e)}")

    def show_data(self, data):
        """Выводит данные в текстовое поле"""
        self.clear_output()

        if not data:
            self.output.insert(tk.END, "Нет данных для отображения")
            return

        self.output.insert(tk.END, f"Данные для {self.asset.get()}:\n\n")

        # Выводим последние 10 записей (чтобы не перегружать интерфейс)
        for item in data[-10:]:
            date = item.get('date', '')
            price = item.get('close', '')
            self.output.insert(tk.END, f"{date}: {price}\n")

    def clear_output(self):
        """Очищает текстовое поле"""
        self.output.delete(1.0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = FinanceApp(root)
    root.mainloop()
