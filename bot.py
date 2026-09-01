import os
import requests
import pandas as pd
import yfinance as yf

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
CHAT_ID = os.environ['CHAT_ID']


def send_telegram_message(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
  try:
    requests.post(url, json=payload)
  except Exception as e:
    print('Telegram error:', e)


symbol = 'BTC-USD'
df = yf.download(symbol, period='5d', interval='5m')
if isinstance(df.columns, pd.MultiIndex):
  df.columns = df.columns.get_level_values(0)
df = df.dropna()


def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
  loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
  rs = gain / loss
  return 100 - (100 / (1 + rs))


df['EMA_8'] = df['Close'].ewm(span=8, adjust=False).mean()
typical_price = (df['High'] + df['Low'] + df['Close']) / 3
df['VWAP'] = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
df['RSI'] = calculate_rsi(df['Close'], 14)
df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()

df['Is_Green'] = (df['Close'] > df['Open']) & (
    (df['Close'] - df['Open']) > (df['High'] - df['Close'])
)
df['Is_Red'] = (df['Close'] < df['Open']) & (
    (df['Open'] - df['Close']) > (df['Close'] - df['Low'])
)

df['Long_Cond'] = (
    (df['Close'] > df['VWAP'])
    & (df['Close'] > df['EMA_8'])
    & df['Is_Green']
    & (df['RSI'] > 50)
    & (df['Volume'] > df['Avg_Volume'])
)

df['Short_Cond'] = (
    (df['Close'] < df['VWAP'])
    & (df['Close'] < df['EMA_8'])
    & df['Is_Red']
    & (df['RSI'] < 50)
    & (df['Volume'] > df['Avg_Volume'])
)

latest_row = df.iloc[-1]
latest_time = df.index[-1]
current_price = latest_row['Close']

if latest_row['Long_Cond']:
  msg = (
      f'🚨 *LONG SIGNAL!*\nSymbol: {symbol}\nPrice: `{current_price:.2f}`\nTime:'
      f' {latest_time}'
  )
  send_telegram_message(msg)
elif latest_row['Short_Cond']:
  msg = (
      f'🚨 *SHORT SIGNAL!*\nSymbol: {symbol}\nPrice: `{current_price:.2f}`\nTime:'
      f' {latest_time}'
  )
  send_telegram_message(msg)
else:
  print(f'No signal at {latest_time}')
