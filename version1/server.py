from flask import Flask, request, jsonify
import random
from datetime import datetime, timedelta

app = Flask(__name__)

# Заглушка для данных (в реальном проекте нужно подключить БД)
fake_data = {
    "Акции": {
        "AAPL": [],
        "GOOGL": [],
        "MSFT": []
    },
    "Криптовалюта": {
        "BTC-USD": [],
        "ETH-USD": []
    },
    "Валюта": {
        "EUR-USD": [],
        "RUB-USD": []
    }
}


# Генерируем фейковые данные при запуске
def generate_fake_data():
    today = datetime.now()
    for asset_type in fake_data:
        for asset in fake_data[asset_type]:
            prices = []
            for i in range(30):  # данные за последние 30 дней
                date = (today - timedelta(days=30 - i)).strftime("%Y-%m-%d")
                base_price = random.uniform(50, 200)
                prices.append({
                    "date": date,
                    "open": round(base_price, 2),
                    "high": round(base_price * 1.05, 2),
                    "low": round(base_price * 0.95, 2),
                    "close": round(base_price * (1 + random.uniform(-0.03, 0.03)), 2)
                })
            fake_data[asset_type][asset] = prices


generate_fake_data()


@app.route('/get_data', methods=['GET'])
def get_data():
    # Получаем параметры из запроса
    asset_type = request.args.get('asset_type')
    asset = request.args.get('asset')

    # Простая проверка входных данных
    if not asset_type or not asset:
        return jsonify({"error": "Не указан тип актива или актив"}), 400

    if asset_type not in fake_data or asset not in fake_data[asset_type]:
        return jsonify({"error": "Актив не найден"}), 404

    # Возвращаем данные для выбранного актива
    return jsonify(fake_data[asset_type][asset])


@app.route('/get_forecast', methods=['GET'])
def get_forecast():
    # Простейший "прогноз" - случайные данные
    asset_type = request.args.get('asset_type')
    asset = request.args.get('asset')

    if not asset_type or not asset:
        return jsonify({"error": "Не указан тип актива или актив"}), 400

    if asset_type not in fake_data or asset not in fake_data[asset_type]:
        return jsonify({"error": "Актив не найден"}), 404

    # Берем последнюю цену
    last_price = fake_data[asset_type][asset][-1]["close"]

    # Генерируем "прогноз" на 7 дней
    forecast = []
    today = datetime.now()
    for i in range(1, 8):
        date = (today + timedelta(days=i)).strftime("%Y-%m-%d")
        forecast.append({
            "date": date,
            "value": round(last_price * (1 + random.uniform(-0.1, 0.1)), 2)
        })

    return jsonify(forecast)


if __name__ == '__main__':
    app.run(debug=True)
