from datetime import datetime, timezone
import os
import numpy as np
import pandas as pd
import requests
import yfinance as yf

# --- TELEGRAM CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv(
    'TELEGRAM_BOT_TOKEN', '8835024039:AAGQDWpkYPQCf4_iAzZmY2OIHvp5wDLPPmE'
)
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '6409092485')
SYMBOL = 'BTC-USD'


def send_telegram_message(message):
  url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
  payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
  try:
    response = requests.post(url, json=payload)
    return response.json()
  except Exception as e:
    print('Telegram error:', e)


def run_crypto_bot():
  print(f'Downloading 5m data for {SYMBOL}...')
  df = yf.download(SYMBOL, period='5d', interval='5m', auto_adjust=False)

  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
  df = df.dropna()

  if len(df) < 50:
    print('Not enough data loaded.')
    return

  # --- RSI Calculation ---
  def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

  # --- Indicators ---
  df['EMA_8'] = df['Close'].ewm(span=8, adjust=False).mean()
  typical_price = (df['High'] + df['Low'] + df['Close']) / 3
  df['VWAP'] = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
  df['RSI'] = calculate_rsi(df['Close'], 14)
  df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()
  df['ATR'] = (
      (df['High'] - df['Low'])
      .rolling(window=14)
      .mean()
  )

  # Candlestick filters
  df['Is_Green'] = (df['Close'] > df['Open']) & (
      (df['Close'] - df['Open']) > (df['High'] - df['Close'])
  )
  df['Is_Red'] = (df['Close'] < df['Open']) & (
      (df['Open'] - df['Close']) > (df['Close'] - df['Low'])
  )
  df = df.dropna()

  # Conditions
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

  # Check Latest Closed Candle (Using -2 to avoid incomplete live candle mismatch)
  i = len(df) - 2
  latest_row = df.iloc[i]
  latest_time = df.index[i]
  current_price = latest_row['Close']
  current_atr = latest_row['ATR']

  signal_found = False
  message_text = ''

  if latest_row['Long_Cond']:
    signal_found = True
    entry_price = current_price
    stop_loss = entry_price - (1.5 * current_atr)
    risk = entry_price - stop_loss
    take_profit = entry_price + (risk * 2.5)  # 1:2.5 Risk-Reward

    message_text = (
        f'🚨 *LONG SIGNAL & RISK MGMT* 🚨\n'
        f'━━━━━━━━━━━━━━━━━━━\n'
        f'📌 *Symbol:* {SYMBOL}\n'
        f'🟢 *Direction:* **BUY / LONG**\n'
        f'💰 *Entry Price:* `{entry_price:.2f}`\n'
        f'🛑 *Stop Loss:* `{stop_loss:.2f}`\n'
        f'🎯 *Take Profit:* `{take_profit:.2f}`\n'
        f'⚖️ *Risk/Reward:* 1:2.5\n'
        f'⏰ *Time:* {latest_time}\n'
        f'━━━━━━━━━━━━━━━━━━━'
    )
  elif latest_row['Short_Cond']:
    signal_found = True
    entry_price = current_price
    stop_loss = entry_price + (1.5 * current_atr)
    risk = stop_loss - entry_price
    take_profit = entry_price - (risk * 2.5)  # 1:2.5 Risk-Reward

    message_text = (
        f'🚨 *SHORT SIGNAL & RISK MGMT* 🚨\n'
        f'━━━━━━━━━━━━━━━━━━━\n'
        f'📌 *Symbol:* {SYMBOL}\n'
        f'🔴 *Direction:* **SELL / SHORT**\n'
        f'💰 *Entry Price:* `{entry_price:.2f}`\n'
        f'🛑 *Stop Loss:* `{stop_loss:.2f}`\n'
        f'🎯 *Take Profit:* `{take_profit:.2f}`\n'
        f'⚖️ *Risk/Reward:* 1:2.5\n'
        f'⏰ *Time:* {latest_time}\n'
        f'━━━━━━━━━━━━━━━━━━━'
    )
  else:
    print(
        f'Current Time {latest_time} par koi naya signal nahi hai. Current'
        f' Price: {current_price:.2f}'
    )

  if signal_found:
    send_telegram_message(message_text)
    print('Signal mil gaya aur Risk Management ke sath Telegram par bhej diya!')
  else:
    print('Koi signal nahi mila.')


if __name__ == '__main__':
  run_crypto_bot()
  
