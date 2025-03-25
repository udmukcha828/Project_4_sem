import sys
import requests
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QComboBox, QDateEdit, QTableWidget, QTableWidgetItem,
                             QTabWidget, QMessageBox)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime


class FinancialAnalysisApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Анализатор финансовых данных")
        self.setGeometry(100, 100, 900, 600)

        # Основные параметры
        self.server_url = "http://localhost:5000"  # URL сервера
        self.asset_types = ["Акции", "Криптовалюта", "Валюта"]
        self.assets = {
            "Акции": ["AAPL", "GOOGL", "MSFT", "AMZN"],
            "Криптовалюта": ["BTC-USD", "ETH-USD", "XRP-USD"],
            "Валюта": ["EUR-USD", "GBP-USD", "JPY-USD"]
        }

        self.init_ui()

    def init_ui(self):
        # Главный виджет и layout
        main_widget = QWidget()
        main_layout = QVBoxLayout()

        # Панель управления
        control_panel = QWidget()
        control_layout = QHBoxLayout()

        # Выбор типа актива
        self.asset_type_combo = QComboBox()
        self.asset_type_combo.addItems(self.asset_types)
        self.asset_type_combo.currentTextChanged.connect(self.update_asset_combo)

        # Выбор конкретного актива
        self.asset_combo = QComboBox()
        self.update_asset_combo(self.asset_types[0])

        # Выбор дат
        self.start_date_edit = QDateEdit(QDate.currentDate().addMonths(-1))
        self.end_date_edit = QDateEdit(QDate.currentDate())

        # Кнопка запроса
        self.request_btn = QPushButton("Получить данные")
        self.request_btn.clicked.connect(self.get_financial_data)

        # Добавление элементов на панель управления
        control_layout.addWidget(QLabel("Тип актива:"))
        control_layout.addWidget(self.asset_type_combo)
        control_layout.addWidget(QLabel("Актив:"))
        control_layout.addWidget(self.asset_combo)
        control_layout.addWidget(QLabel("С:"))
        control_layout.addWidget(self.start_date_edit)
        control_layout.addWidget(QLabel("По:"))
        control_layout.addWidget(self.end_date_edit)
        control_layout.addWidget(self.request_btn)

        control_panel.setLayout(control_layout)

        # Вкладки для отображения результатов
        self.tabs = QTabWidget()

        # Вкладка с графиком
        self.graph_tab = QWidget()
        self.graph_layout = QVBoxLayout()

        self.figure = Figure(figsize=(10, 5))
        self.canvas = FigureCanvas(self.figure)
        self.graph_layout.addWidget(self.canvas)

        self.graph_tab.setLayout(self.graph_layout)

        # Вкладка с таблицей
        self.table_tab = QWidget()
        self.table_layout = QVBoxLayout()

        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["Дата", "Цена открытия", "Максимум", "Минимум", "Цена закрытия"])
        self.data_table.setSortingEnabled(True)

        self.table_layout.addWidget(self.data_table)
        self.table_tab.setLayout(self.table_layout)

        # Вкладка с прогнозом
        self.forecast_tab = QWidget()
        self.forecast_layout = QVBoxLayout()

        self.forecast_figure = Figure(figsize=(10, 5))
        self.forecast_canvas = FigureCanvas(self.forecast_figure)
        self.forecast_layout.addWidget(self.forecast_canvas)

        self.forecast_btn = QPushButton("Получить прогноз")
        self.forecast_btn.clicked.connect(self.get_forecast)
        self.forecast_layout.addWidget(self.forecast_btn)

        self.forecast_tab.setLayout(self.forecast_layout)

        # Добавление вкладок
        self.tabs.addTab(self.graph_tab, "График")
        self.tabs.addTab(self.table_tab, "Таблица данных")
        self.tabs.addTab(self.forecast_tab, "Прогноз")

        # Добавление элементов в главный layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.tabs)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

    def update_asset_combo(self, asset_type):
        """Обновляет список активов при изменении типа актива"""
        self.asset_combo.clear()
        self.asset_combo.addItems(self.assets.get(asset_type, []))

    def get_financial_data(self):
        """Запрашивает данные с сервера"""
        asset_type = self.asset_type_combo.currentText()
        asset = self.asset_combo.currentText()
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")

        try:
            # Формируем запрос к серверу
            params = {
                "asset_type": asset_type,
                "asset": asset,
                "start_date": start_date,
                "end_date": end_date
            }

            response = requests.get(f"{self.server_url}/get_data", params=params)

            if response.status_code == 200:
                data = response.json()
                self.display_data(data)
            else:
                QMessageBox.warning(self, "Ошибка", f"Ошибка сервера: {response.text}")

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу: {str(e)}")

    def display_data(self, data):
        """Отображает полученные данные в интерфейсе"""
        if not data:
            QMessageBox.information(self, "Информация", "Нет данных для отображения")
            return

        # Преобразуем данные в DataFrame для удобства
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])
        df.sort_values('date', inplace=True)

        # Отображаем данные в таблице
        self.display_table_data(df)

        # Отображаем график
        self.plot_data(df)

    def display_table_data(self, df):
        """Заполняет таблицу данными"""
        self.data_table.setRowCount(len(df))

        for row_idx, row in df.iterrows():
            self.data_table.setItem(row_idx, 0, QTableWidgetItem(row['date'].strftime("%Y-%m-%d")))
            self.data_table.setItem(row_idx, 1, QTableWidgetItem(str(row['open'])))
            self.data_table.setItem(row_idx, 2, QTableWidgetItem(str(row['high'])))
            self.data_table.setItem(row_idx, 3, QTableWidgetItem(str(row['low'])))
            self.data_table.setItem(row_idx, 4, QTableWidgetItem(str(row['close'])))

    def plot_data(self, df):
        """Строит график цен"""
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        ax.plot(df['date'], df['close'], label='Цена закрытия', linewidth=2)
        ax.set_title(f"Динамика цен для {self.asset_combo.currentText()}")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Цена")
        ax.legend()
        ax.grid(True)

        # Форматирование дат на оси X
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        self.figure.autofmt_xdate()

        self.canvas.draw()

    def get_forecast(self):
        """Запрашивает прогноз у сервера"""
        asset_type = self.asset_type_combo.currentText()
        asset = self.asset_combo.currentText()

        try:
            params = {
                "asset_type": asset_type,
                "asset": asset
            }

            response = requests.get(f"{self.server_url}/get_forecast", params=params)

            if response.status_code == 200:
                forecast_data = response.json()
                self.display_forecast(forecast_data)
            else:
                QMessageBox.warning(self, "Ошибка", f"Ошибка сервера: {response.text}")

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось подключиться к серверу: {str(e)}")

    def display_forecast(self, forecast_data):
        """Отображает прогноз"""
        if not forecast_data:
            QMessageBox.information(self, "Информация", "Нет данных прогноза")
            return

        self.forecast_figure.clear()
        ax = self.forecast_figure.add_subplot(111)

        # Преобразуем данные прогноза
        dates = [datetime.strptime(d['date'], "%Y-%m-%d") for d in forecast_data]
        values = [d['value'] for d in forecast_data]

        ax.plot(dates, values, label='Прогноз', linewidth=2, color='red')
        ax.set_title(f"Прогноз цен для {self.asset_combo.currentText()}")
        ax.set_xlabel("Дата")
        ax.set_ylabel("Цена")
        ax.legend()
        ax.grid(True)

        # Форматирование дат на оси X
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        self.forecast_figure.autofmt_xdate()

        self.forecast_canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FinancialAnalysisApp()
    window.show()
    sys.exit(app.exec_())
