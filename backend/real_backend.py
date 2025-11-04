"""Realtime backend streamer: connects to Binance futures, buffers ticks, persists to SQLite."""
import asyncio, json, sqlite3, time, threading, os
from collections import defaultdict, deque
import websockets

BASE = os.path.dirname(__file__)
DBPATH = os.path.join(BASE, '..', 'data_ticks.db')
try:
    from pymongo import MongoClient
except Exception:
    MongoClient = None
MONGO_URI = os.getenv('MONGODB_URI')
MONGO_DB = os.getenv('MONGODB_DB', 'quant')
MONGO_COLL = os.getenv('MONGODB_COLLECTION', 'ticks')
mongo_client = None
mongo_col = None

def init_mongo():
    global mongo_client, mongo_col
    if not MONGO_URI or MongoClient is None:
        return
    try:
        mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client[MONGO_DB]
        mongo_col = db[MONGO_COLL]
        mongo_col.create_index([('symbol', 1), ('ts', 1)])
    except Exception as e:
        print('mongo init error', e)

def init_db():
    conn = sqlite3.connect(DBPATH)
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS ticks (id INTEGER PRIMARY KEY, ts INTEGER, symbol TEXT, price REAL, qty REAL)''')
    cur.execute('CREATE INDEX IF NOT EXISTS ix_ticks_symbol_ts ON ticks(symbol, ts)')
    conn.commit(); conn.close()

init_db()
init_mongo()

BUFFER_MAX = 200000
tick_storage = defaultdict(lambda: deque(maxlen=BUFFER_MAX))
stop_event = threading.Event()
_runner_thread = None
_persist_thread = None
_loop = None

async def _stream_symbols(symbols):
    streams = '/'.join(f"{s.lower()}@trade" for s in symbols)
    uri = f"wss://fstream.binance.com/stream?streams={streams}"
    print('Connecting to', uri)
    async with websockets.connect(uri, ping_interval=20) as ws:
        async for raw in ws:
            try:
                msg = json.loads(raw)
                payload = msg.get('data', msg)
                sym = payload.get('s')
                price = float(payload.get('p', 0.0))
                qty = float(payload.get('q', 0.0))
                ts = int(payload.get('T') or payload.get('E') or int(time.time()*1000))
                tick = {'timestamp': ts, 'symbol': sym, 'price': price, 'qty': qty}
                tick_storage[sym].append(tick)
            except Exception as e:
                print('parse error', e)
            if stop_event.is_set():
                break

def persist_loop(interval=5):
    while not stop_event.is_set():
        try:
            conn = sqlite3.connect(DBPATH)
            cur = conn.cursor()
            # move from buffer to DB
            for sym, dq in list(tick_storage.items()):
                rows = []
                docs = []
                while dq:
                    t = dq.popleft()
                    rows.append((int(t['timestamp']), t['symbol'], float(t['price']), float(t['qty'])))
                    docs.append({'ts': int(t['timestamp']), 'symbol': t['symbol'], 'price': float(t['price']), 'qty': float(t['qty'])})
                    if len(rows) >= 500:
                        cur.executemany('INSERT INTO ticks (ts,symbol,price,qty) VALUES (?,?,?,?)', rows)
                        conn.commit(); rows = []
                        if mongo_col is not None and docs:
                            try:
                                mongo_col.insert_many(docs, ordered=False)
                            except Exception as me:
                                print('mongo insert error', me)
                            docs = []
                if rows:
                    cur.executemany('INSERT INTO ticks (ts,symbol,price,qty) VALUES (?,?,?,?)', rows)
                    conn.commit()
                if mongo_col is not None and docs:
                    try:
                        mongo_col.insert_many(docs, ordered=False)
                    except Exception as me:
                        print('mongo insert error', me)
            conn.close()
        except Exception as e:
            print('persist error', e)
        time.sleep(interval)

def start_background_stream(symbols=None):
    if symbols is None:
        symbols = ['BTCUSDT','ETHUSDT']
    global _runner_thread, _persist_thread, _loop
    if _runner_thread and _runner_thread.is_alive():
        print('Streamer already running')
        return
    stop_event.clear()
    def runner():
        global _loop
        loop = asyncio.new_event_loop()
        _loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_stream_symbols(symbols))
    _persist_thread = threading.Thread(target=persist_loop, daemon=True)
    _persist_thread.start()
    _runner_thread = threading.Thread(target=runner, daemon=True)
    _runner_thread.start()
    print('Background streamer started for', symbols)

def stop_background_stream(timeout=5):
    global _runner_thread, _persist_thread, _loop
    if not (_runner_thread and _runner_thread.is_alive()):
        stop_event.set()
        return
    stop_event.set()
    try:
        if _loop:
            _loop.call_soon_threadsafe(_loop.stop)
    except Exception:
        pass
    if _persist_thread:
        _persist_thread.join(timeout=timeout)
    if _runner_thread:
        _runner_thread.join(timeout=timeout)
    _runner_thread = None
    _persist_thread = None
    _loop = None
    print('Background streamer stopped')

if __name__ == '__main__':
    start_background_stream(['BTCUSDT','ETHUSDT'])
    while True:
        time.sleep(1)
