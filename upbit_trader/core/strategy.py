from __future__ import annotations
import pandas as pd


def calc_rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def get_signal(
    df: pd.DataFrame,
    ma_short: int = 5,
    ma_long: int = 20,
    rsi_period: int = 14,
    rsi_buy: float = 50,
    rsi_sell: float = 70,
    use_golden_cross: bool = True,
    use_rsi_buy: bool = True,
    use_rsi_sell: bool = True,
) -> tuple[str, dict]:
    """골든크로스 + RSI 전략. 'buy' / 'sell' / 'hold' 반환."""
    if df is None or len(df) < ma_long + 2:
        return "hold", {}

    closes = df["close"]
    ma5 = closes.rolling(ma_short).mean()
    ma20 = closes.rolling(ma_long).mean()
    rsi = calc_rsi(closes, rsi_period)

    prev5, curr5 = ma5.iloc[-2], ma5.iloc[-1]
    prev20, curr20 = ma20.iloc[-2], ma20.iloc[-1]
    curr_rsi = rsi.iloc[-1]

    golden = prev5 <= prev20 and curr5 > curr20
    dead = prev5 >= prev20 and curr5 < curr20

    # 매수: 활성화된 조건이 모두 충족되어야 함
    buy_conditions = []
    if use_golden_cross:
        buy_conditions.append(bool(golden))
    if use_rsi_buy:
        buy_conditions.append(float(curr_rsi) < rsi_buy)

    # 매도: 활성화된 조건 중 하나라도 충족되면 매도
    sell_conditions = []
    if use_golden_cross:
        sell_conditions.append(bool(dead))
    if use_rsi_sell:
        sell_conditions.append(float(curr_rsi) > rsi_sell)

    if buy_conditions and all(buy_conditions):
        signal = "buy"
    elif sell_conditions and any(sell_conditions):
        signal = "sell"
    else:
        signal = "hold"

    indicators = {
        "ma5": round(float(curr5), 0),
        "ma20": round(float(curr20), 0),
        "rsi": round(float(curr_rsi), 2),
        "golden_cross": bool(golden),
        "dead_cross": bool(dead),
    }
    return signal, indicators
