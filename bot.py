from datetime import datetime, timezone
import os
import numpy as np
import pandas as pd
import requests
import yfinance as yf

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
SYMBOL = 'BTC-USD'  # Ya 'GC=F' Gold ke liye


def send_telegram_message(message):
  if not TELEGRAM_BOT_TOKEN:
    return
  url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
  payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
  requests.post(url, json=payload)


def run_bot():
  df = yf.download(SYMBOL, period='30d', interval='1h', auto_adjust=False)
  if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)
  df = df.dropna()

  if len(df) < 50:
    return

  df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
  df['Avg_Volume'] = df['Volume'].rolling(window=20).mean()
  df['ATR'] = (df['High'] - df['Low']).rolling(window=14).mean()
  df = df.dropna()

  # Hum hamesha CLOSED candles par check karenge (-3, -2, -1) taaki live price mismatch na ho
  i = len(df) - 2
  resistance_level = df['High'].iloc[i - 30 : i - 1].max()

  prev_c = df.iloc[i]
  curr_c = df.iloc[i + 1]  # Latest closed candle
  current_atr = curr_c['ATR']

  is_breakout = (prev_c['Close'] > resistance_level) and (
      prev_c['Volume'] > prev_c['Avg_Volume']
  )
  is_retest = (
      curr_c['Low'] <= resistance_level + (current_atr * 0.5)
      and curr_c['Low'] >= resistance_level - (current_atr * 0.5)
  )
  is_rejection = curr_c['Close'] > curr_c['Open']
  is_trend_up = curr_c['Close'] > curr_c['EMA_50']

  if is_breakout and is_retest and is_rejection and is_trend_up:
    entry_price = curr_c['Close']
    stop_loss = entry_price - (1.5 * current_atr)
    risk = entry_price - stop_loss
    take_profit = entry_price + (risk * 2.5)

    message = (
        f'🚨 *LONG SIGNAL CONFIRMED!* 🚨\n'
        f'━━━━━━━━━━━━━━━━━━━\n'
        f'📌 *Symbol:* {SYMBOL}\n'
        f'🟢 *Entry:* {entry_price:.2f}\n'
        f'🛑 *Stop Loss:* {stop_loss:.2f}\n'
        f'🎯 *Take Profit:* {take_profit:.2f}\n'
        f'⏰ *Time:* {curr_c.name}\n'
        f'━━━━━━━━━━━━━━━━━━━'
    )
    send_telegram_message(message)


if __name__ == '__main__':
  run_bot()
  
