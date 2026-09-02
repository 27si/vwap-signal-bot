from datetime import datetime, timedelta, timezone
import os
import pandas as pd
import requests
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
df = yf.download(symbol, period='5d', interval='5m', progress=False)
if isinstance(df.columns, pd.MultiIndex):
  df.columns = df.columns.get_level_values(0)
df = df.dropna()


def calculate_rsi(series, period=14):
  delta = series.diff()
  gain = delta.where(delta > 0, 0).rolling(window=period).mean()
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
prev_row = df.iloc[-2]
current_price = latest_row['Close']

# UTC time ko Indian Standard Time (IST) me convert karne ke liye (+5:30)
utc_time = df.index[-1]
if utc_time.tzinfo is None:
  utc_time = utc_time.tz_localize('UTC')
ist_time = utc_time.astimezone(timezone(timedelta(hours=5, minutes=30)))
formatted_time = ist_time.strftime('%Y-%m-%d %H:%M:%S IST')

if latest_row['Long_Cond']:
  entry_price = current_price
  stop_loss = latest_row['Low'] - 10  # Candle low ke thoda niche SL
  risk = entry_price - stop_loss
  take_profit = entry_price + (risk * 2)  # 1:2 Target

  msg = (
      f'🚨 *LONG SIGNAL!*\n'
      f'━━━━━━━━━━━━━━━━━━━\n'
      f'📌 **Symbol:** {symbol}\n'
      f'🟢 **Entry:** `{entry_price:.2f}`\n'
      f'🛑 **Stop Loss:** `{stop_loss:.2f}`\n'
      f'🎯 **Take Profit:** `{take_profit:.2f}`\n'
      f'⏰ **Time:** {formatted_time}\n'
      f'━━━━━━━━━━━━━━━━━━━'
  )
  send_telegram_message(msg)

elif latest_row['Short_Cond']:
  entry_price = current_price
  stop_loss = latest_row['High'] + 10  # Candle high ke thoda upar SL
  risk = stop_loss - entry_price
  take_profit = entry_price - (risk * 2)  # 1:2 Target

  msg = (
      f'🚨 *SHORT SIGNAL!*\n'
      f'━━━━━━━━━━━━━━━━━━━\n'
      f'📌 **Symbol:** {symbol}\n'
      f'🔴 **Entry:** `{entry_price:.2f}`\n'
      f'🛑 **Stop Loss:** `{stop_loss:.2f}`\n'
      f'🎯 **Take Profit:** `{take_profit:.2f}`\n'
      f'⏰ **Time:** {formatted_time}\n'
      f'━━━━━━━━━━━━━━━━━━━'
  )
  send_telegram_message(msg)

else:
  print(f'No signal at {formatted_time}')
