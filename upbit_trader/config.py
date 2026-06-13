APP_NAME = "Upbit 자동매매"
APP_VERSION = "0.2.0"

DEFAULT_TICKER = "KRW-BTC"
DEFAULT_TRADE_AMOUNT = 10000   # 원
CANDLE_INTERVAL = "minute60"   # 1시간봉
MA_SHORT = 5
MA_LONG = 20
RSI_PERIOD = 14
RSI_BUY = 50    # RSI 이하일 때 골든크로스 매수
RSI_SELL = 70   # RSI 이상일 때 매도
LOOP_INTERVAL = 60  # 초 (1분마다 체크)
MAX_TRADES = 200    # 최대 보관 거래 내역
