import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(layout="wide", page_title="Currency Forecast", page_icon="💹")

# Стили
st.markdown("""
<style>
.stMetric {border: 1px solid #f0f2f6; border-radius: 5px; padding: 15px;}
.stButton>button {width: 100%;}
.plot-container {margin-top: 30px;}
</style>
""", unsafe_allow_html=True)

SERVER_URL = "http://127.0.0.1:8000"
CURRENCIES = ["USD", "EUR", "RUB"]

def check_server():
    try:
        response = requests.get(f"{SERVER_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

@st.cache_data(ttl=60*5)
def get_forecast(from_curr, to_curr, model_type, history_days, forecast_days):
    try:
        response = requests.get(
            f"{SERVER_URL}/forecast/{from_curr}/{to_curr}",
            params={
                "model_type": model_type,
                "history_days": history_days,
                "forecast_days": forecast_days
            },
            timeout=15
        )
        return response.json() if response.status_code == 200 else None
    except:
        return None

def display_forecast(data, from_curr, to_curr):
    if not data or "history" not in data or not data["history"].get("dates"):
        st.error("Нет данных для отображения")
        return

    fig = go.Figure()

    # Исторические данные
    fig.add_trace(go.Scatter(
        x=data["history"]["dates"],
        y=data["history"]["rates"],
        name="История",
        line=dict(color="#1f77b4", width=2),
        mode="lines"
    ))

    # Прогноз
    if data.get("dates") and data.get("rates"):
        fig.add_trace(go.Scatter(
            x=data["dates"],
            y=data["rates"],
            name=f"Прогноз ({data['model']})",
            line=dict(color="#ff7f0e", width=3, dash="dash"),
            mode="lines+markers"
        ))

    # Разделительная линия
    if data["history"]["dates"]:
        fig.add_shape(
            type="line",
            x0=data["history"]["dates"][-1],
            x1=data["history"]["dates"][-1],
            y0=min(data["history"]["rates"] + data.get("rates", [])),
            y1=max(data["history"]["rates"] + data.get("rates", [])),
            line=dict(color="gray", width=2, dash="dot")
        )
        fig.add_annotation(
            x=data["history"]["dates"][-1],
            y=max(data["history"]["rates"]),
            text="Начало прогноза",
            showarrow=True,
            arrowhead=1
        )

    fig.update_layout(
        title=f"Курс {from_curr}/{to_curr}",
        xaxis_title="Дата",
        yaxis_title="Курс",
        hovermode="x unified",
        height=600
    )

    st.plotly_chart(fig, use_container_width=True)

    # Метрики
    if "last_rate" in data and "rates" in data and data["rates"]:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Текущий курс", f"{data['last_rate']:.4f}")
        with col2:
            change = data["rates"][-1] - data["last_rate"]
            st.metric(
                "Прогнозируемый курс",
                f"{data['rates'][-1]:.4f}",
                delta=f"{change:.4f}"
            )

def main():
    st.title("📈 Прогноз валютных курсов")

    if not check_server():
        st.error("Сервер не доступен. Запустите сначала server.py")
        return

    col1, col2 = st.columns(2)
    with col1:
        from_curr = st.selectbox("Из", CURRENCIES, index=0)
    with col2:
        to_curr = st.selectbox("В", CURRENCIES, index=1)

    model_type = st.selectbox(
        "Модель",
        ["linear", "arima", "gbm", "ensemble"],
        format_func=lambda x: {
            "linear": "Линейная регрессия",
            "arima": "ARIMA",
            "gbm": "Градиентный бустинг",
            "ensemble": "Ансамбль моделей"
        }[x]
    )

    history_days = st.slider("Дней истории", 30, 365, 180)
    forecast_days = st.slider("Дней прогноза", 7, 90, 30)

    if st.button("Получить прогноз", type="primary"):
        with st.spinner("Формирование прогноза..."):
            data = get_forecast(from_curr, to_curr, model_type, history_days, forecast_days)
            display_forecast(data, from_curr, to_curr)

if __name__ == "__main__":
    main()
