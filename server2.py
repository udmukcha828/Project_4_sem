from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import GradientBoostingRegressor
from datetime import datetime, timedelta
import logging
import os
import time
from typing import List, Any, Optional
from functools import lru_cache
import uvicorn
from pydantic import BaseModel

# Настройка приложения
app = FastAPI(
    title="Currency Forecast API",
    version="5.2",
    description="API для прогнозирования курсов RUB, USD и EUR"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


# Модели данных
class HistoryData(BaseModel):
    dates: List[str]
    rates: List[float]


class ForecastResponse(BaseModel):
    model: str
    dates: List[str]
    rates: List[float]
    history: HistoryData
    last_rate: float
    status: str
    execution_time: float
    message: Optional[str] = None


# Конфигурация API
API_CONFIG = {
    "alphavantage": {
        "url": "https://www.alphavantage.co/query",
        "api_key": "DVKDVPGWZUN91KH7",
        "function": "FX_DAILY"
    },
    "frankfurter": {
        "url": "https://api.frankfurter.app",
        "max_days": 365
    }
}

MAX_HISTORY_DAYS = 730
MAX_FORECAST_DAYS = 90
SUPPORTED_CURRENCIES = ["USD", "EUR", "RUB"]

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def get_alpha_vantage_data(from_curr: str, to_curr: str) -> pd.DataFrame:
    """Получение данных от Alpha Vantage"""
    if from_curr not in SUPPORTED_CURRENCIES or to_curr not in SUPPORTED_CURRENCIES:
        return pd.DataFrame()

    params = {
        "function": API_CONFIG["alphavantage"]["function"],
        "from_symbol": from_curr,
        "to_symbol": to_curr,
        "apikey": API_CONFIG["alphavantage"]["api_key"],
        "outputsize": "full"
    }

    try:
        response = requests.get(API_CONFIG["alphavantage"]["url"], params=params, timeout=10)
        data = response.json()

        if "Time Series FX (Daily)" in data:
            df = pd.DataFrame(data["Time Series FX (Daily)"]).T
            df.index = pd.to_datetime(df.index)
            df = df.rename(columns={"4. close": "close"})[["close"]]
            df['close'] = df['close'].apply(safe_float)
            return df.sort_index()
    except Exception as e:
        logger.error(f"Alpha Vantage error: {str(e)}")

    return pd.DataFrame()


def get_frankfurter_data(from_curr: str, to_curr: str) -> pd.DataFrame:
    """Получение данных от Frankfurter API"""
    if from_curr not in ["USD", "EUR"] or to_curr not in ["USD", "EUR"]:
        return pd.DataFrame()

    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=API_CONFIG["frankfurter"]["max_days"])

    try:
        url = f"{API_CONFIG['frankfurter']['url']}/{start_date}..{end_date}?from={from_curr}&to={to_curr}"
        response = requests.get(url, timeout=10)
        data = response.json()

        if "rates" in data and data["rates"]:
            df = pd.DataFrame.from_dict(data["rates"], orient="index", columns=["close"])
            df.index = pd.to_datetime(df.index)
            df['close'] = df['close'].apply(safe_float)
            return df.sort_index()
    except Exception as e:
        logger.error(f"Frankfurter error: {str(e)}")

    return pd.DataFrame()


@lru_cache(maxsize=32)
def get_currency_data(from_curr: str, to_curr: str) -> pd.DataFrame:
    """Получение данных с приоритетом по источникам"""
    sources = [get_frankfurter_data, get_alpha_vantage_data]

    for source in sources:
        df = source(from_curr, to_curr)
        if not df.empty:
            logger.info(f"Using data from {source.__name__} for {from_curr}/{to_curr}")
            return df

    logger.error(f"No data available for {from_curr}/{to_curr}")
    return pd.DataFrame()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "supported_currencies": SUPPORTED_CURRENCIES
    }


@app.get("/forecast/{from_curr}/{to_curr}", response_model=ForecastResponse)
async def get_forecast(
        from_curr: str,
        to_curr: str,
        model_type: str = Query("linear"),
        history_days: int = Query(180, ge=30, le=MAX_HISTORY_DAYS),
        forecast_days: int = Query(30, ge=7, le=MAX_FORECAST_DAYS)
):
    start_time = time.time()

    try:
        from_curr = from_curr.upper()
        to_curr = to_curr.upper()

        if from_curr not in SUPPORTED_CURRENCIES or to_curr not in SUPPORTED_CURRENCIES:
            raise HTTPException(status_code=400, detail="Unsupported currency pair")

        if from_curr == to_curr:
            raise HTTPException(status_code=400, detail="Currencies must be different")

        full_df = get_currency_data(from_curr, to_curr)

        if full_df.empty:
            raise HTTPException(status_code=404, detail="Currency data not available")

        cutoff_date = full_df.index[-1] - pd.Timedelta(days=min(history_days, len(full_df)))
        df = full_df.loc[full_df.index >= cutoff_date]

        if len(df) < 30:
            df = full_df.tail(30)
            logger.warning(f"Using only {len(df)} days of data")

        history_dates = [date.strftime("%Y-%m-%d") for date in df.index]
        future_dates = [
            (df.index[-1] + timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(1, forecast_days + 1)
        ]
        y = df['close'].values.astype(float)

        if model_type == "linear":
            model = LinearRegression()
            X = np.arange(len(y)).reshape(-1, 1)
            model.fit(X, y)
            future_y = model.predict(np.arange(len(y), len(y) + forecast_days).reshape(-1, 1))

        elif model_type == "arima":
            model = ARIMA(y, order=(1, 1, 1))
            model_fit = model.fit()
            future_y = model_fit.forecast(steps=forecast_days)

        elif model_type == "gbm":
            df_features = pd.DataFrame({
                'day_of_week': df.index.dayofweek,
                'month': df.index.month,
                'trend': np.arange(len(df))
            })

            model = GradientBoostingRegressor(n_estimators=50, random_state=42)
            model.fit(df_features, y)

            future_features = pd.DataFrame({
                'day_of_week': [(df.index[-1] + timedelta(days=i)).dayofweek
                                for i in range(1, forecast_days + 1)],
                'month': [(df.index[-1] + timedelta(days=i)).month
                          for i in range(1, forecast_days + 1)],
                'trend': np.arange(len(y), len(y) + forecast_days)
            })
            future_y = model.predict(future_features)

        elif model_type == "ensemble":
            linear = LinearRegression()
            X = np.arange(len(y)).reshape(-1, 1)
            linear.fit(X, y)
            linear_pred = linear.predict(np.arange(len(y), len(y) + forecast_days).reshape(-1, 1))

            try:
                arima = ARIMA(y, order=(1, 1, 1))
                arima_fit = arima.fit()
                arima_pred = arima_fit.forecast(steps=forecast_days)
            except:
                arima_pred = linear_pred.copy()

            future_y = (linear_pred.flatten() * 0.5) + (arima_pred * 0.5)

        execution_time = time.time() - start_time

        return ForecastResponse(
            model=model_type,
            dates=future_dates,
            rates=[round(float(x), 4) for x in future_y],
            history=HistoryData(
                dates=history_dates,
                rates=[round(float(x), 4) for x in y]
            ),
            last_rate=round(float(y[-1]), 4),
            status="success",
            execution_time=round(execution_time, 2),
            message=f"Forecast for {from_curr}/{to_curr} completed"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Forecast error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
