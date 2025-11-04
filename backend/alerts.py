import threading, time
from .storage import get_resampled
from .analytics import compute_spread_zscore
ALERTS = []
def add_alert(a):
    ALERTS.append(a); return a
def check_loop(interval=5):
    while True:
        try:
            for a in list(ALERTS):
                if a.get('metric')=='zscore' and len(a.get('symbols',[]))>=2:
                    s1,s2 = a['symbols'][:2]
                    df1=get_resampled(s1,a.get('tf','1Min')); df2=get_resampled(s2,a.get('tf','1Min'))
                    if df1.empty or df2.empty: continue
                    spread,z = compute_spread_zscore(df1,df2,a.get('hedge_ratio',1.0), a.get('window',20))
                    val = float(z.dropna().iloc[-1]) if not z.dropna().empty else None
                    if val is None: continue
                    op = a.get('op','>'); thr = float(a.get('value',2.0))
                    if (op=='>' and val>thr) or (op=='<' and val<thr):
                        print('ALERT TRIGGERED', a)
        except Exception as e:
            print('alert error', e)
        time.sleep(interval)
def start_alert_thread():
    t = threading.Thread(target=check_loop, daemon=True); t.start()
