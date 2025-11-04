import sqlite3, os, pandas as pd
DBPATH = os.path.join(os.path.dirname(__file__), '..', 'data_ticks.db')
def get_recent(symbol, limit=1000):
    conn = sqlite3.connect(DBPATH)
    cur = conn.cursor()
    cur.execute('SELECT ts, price, qty FROM ticks WHERE symbol=? ORDER BY ts DESC LIMIT ?', (symbol, limit))
    rows = cur.fetchall(); conn.close()
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows, columns=['ts','price','qty'])
    df['timestamp'] = pd.to_datetime(df['ts'], unit='ms')
    df = df.set_index('timestamp').sort_index()
    return df[['price','qty']]
def get_resampled(symbol, timeframe='1Min', limit=10000):
    df = get_recent(symbol, limit=limit)
    if df.empty: return df
    # normalize timeframe strings from UI
    tf = timeframe
    if tf.lower() in ['1s','1sec','1second']:
        tf = '1S'
    if tf.lower()=='1min' or tf=='1Min':
        tf = '1Min'
    if tf.lower()=='5min' or tf=='5Min':
        tf = '5Min'
    o = df['price'].resample(tf).ohlc()
    v = df['qty'].resample(tf).sum().rename('volume')
    out = o.join(v); out['price_mean'] = (out['open']+out['close'])/2
    return out.dropna()
