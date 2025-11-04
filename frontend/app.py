# Path fix so backend package is importable when running from frontend/
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st, pandas as pd, numpy as np, plotly.graph_objects as go, json, sqlite3, time
import plotly.io as pio
from backend import start_background_stream, stop_background_stream, tick_storage
from backend.storage import get_resampled
from backend.analytics import compute_spread_zscore, compute_hedge_ratio_kalman, run_adf_test, compute_hedge_ratio_ols, rolling_correlation, compute_price_stats
from backend.alerts import add_alert, start_alert_thread, ALERTS

st.set_page_config(page_title='Quant Analytics Lab', layout='wide')

# session defaults
if 'theme' not in st.session_state: st.session_state.theme='dark'
if 'symbols' not in st.session_state: st.session_state.symbols=['BTCUSDT','ETHUSDT']
if 'backend_started' not in st.session_state: st.session_state.backend_started=False
try:
    from streamlit_autorefresh import st_autorefresh
except Exception:
    st_autorefresh = None

def toggle_theme(): st.session_state.theme = 'light' if st.session_state.theme=='dark' else 'dark'

# Header
c1,c2 = st.columns([7,3])
with c1:
    st.markdown('## 📊 Quant Analytics Lab — Streamlit (Advanced)')
    st.markdown('**Price comparison, spread/z-score, Kalman hedge, rolling correlation & analysis summary**')
with c2:
    if st.button('Toggle Theme'): toggle_theme()
    live = st.session_state.backend_started
    st.markdown('🟢 Live' if live else '🔴 Stopped')

# Sidebar controls
st.sidebar.header('Controls')
colA, colB = st.sidebar.columns(2)
with colA:
    start_clicked = st.button('Start Stream')
with colB:
    stop_clicked = st.button('Stop Stream')
if start_clicked and not st.session_state.backend_started:
    start_background_stream(st.session_state.symbols)
    start_alert_thread()
    st.session_state.backend_started = True
if stop_clicked and st.session_state.backend_started:
    stop_background_stream()
    st.session_state.backend_started = False
st.sidebar.write('Status: Running' if st.session_state.backend_started else 'Status: Stopped')
live_counts = {s: len(tick_storage.get(s, [])) for s in st.session_state.symbols}
total_ticks = sum(live_counts.values())
if st.session_state.backend_started:
    st.sidebar.write(f"Live collecting {len(st.session_state.symbols)} symbol(s)… ({total_ticks} ticks)")
symbols = st.sidebar.multiselect('Symbols (choose 1 or 2)', options=['BTCUSDT','ETHUSDT','BNBUSDT','ADAUSDT','XRPUSDT'], default=st.session_state.symbols)
st.session_state.symbols = symbols or ['BTCUSDT','ETHUSDT']
tf = st.sidebar.selectbox('Timeframe', ['1S','1Min','5Min'], index=1)
window = st.sidebar.slider('Rolling window (bars)', min_value=5, max_value=200, value=30)
corr_window = st.sidebar.slider('Correlation window (bars)', min_value=5, max_value=200, value=20)

# Auto refresh while running
if st.session_state.backend_started and st_autorefresh is not None:
    st_autorefresh(interval=2000, key='live_refresh')

# NDJSON upload
st.sidebar.subheader('Upload NDJSON (collector output)')
uploaded = st.sidebar.file_uploader('Upload NDJSON', type=['ndjson','json','csv'])
if uploaded:
    raw = uploaded.read().decode(errors='ignore')
    lines = [l for l in raw.splitlines() if l.strip()]
    conn = sqlite3.connect(os.path.join('.', 'data_ticks.db')); cur = conn.cursor()
    skipped = 0; inserted = 0
    for line in lines:
        try:
            j = json.loads(line)
            if not isinstance(j, dict): skipped += 1; continue
            ts = int(j.get('ts') or j.get('timestamp') or int(time.time()*1000))
            sym = j.get('symbol') or j.get('s') or 'UNKNOWN'
            price = float(j.get('price') or j.get('p') or 0.0); qty = float(j.get('size') or j.get('q') or j.get('qty') or 0.0)
            cur.execute('INSERT INTO ticks (ts,symbol,price,qty) VALUES (?,?,?,?)', (ts,sym,price,qty))
            inserted += 1
        except Exception as e:
            skipped += 1
    conn.commit(); conn.close()
    st.success(f'Uploaded NDJSON: inserted={inserted}, skipped={skipped}')

# Main layout
cols = st.columns([3,1])
with cols[0]:
    st.subheader('Price Comparison & Candlestick')
    primary = st.session_state.symbols[0]
    df = get_resampled(primary, timeframe=('1Min' if tf=='1Min' else '1S' if tf=='1S' else '5Min'))
    if df is None or df.empty:
        st.info('No resampled data yet. Wait for backend to collect ticks or upload NDJSON.')
    else:
        # Price comparison overlay if second symbol selected
        fig = go.Figure()
        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name=primary))
        if len(st.session_state.symbols) >= 2:
            secondary = st.session_state.symbols[1]
            df2 = get_resampled(secondary, timeframe=('1Min' if tf=='1Min' else '1S' if tf=='1S' else '5Min'))
            if not df2.empty:
                # overlay secondary close as line (resampled to same index)
                df2a = df2['close'].reindex(df.index, method='nearest', tolerance=pd.Timedelta('1min')).ffill()
                fig.add_trace(go.Scatter(x=df2a.index, y=df2a.values, mode='lines', name=secondary, yaxis='y2'))
                # add secondary axis
                fig.update_layout(yaxis2=dict(overlaying='y', side='right', showgrid=False, title=secondary+' Price'))
        fig.update_layout(height=420, template='plotly_dark' if st.session_state.theme=='dark' else 'plotly', legend=dict(orientation='h'))
        st.plotly_chart(fig, use_container_width=True)
        # Download price chart PNG
        try:
            png_price = pio.to_image(fig, format='png', scale=2)
            st.download_button('Download Price Chart PNG', data=png_price, file_name=f'price_{primary}.png', mime='image/png')
        except Exception:
            pass

        # Spread & z-score over time + analysis summary
        if len(st.session_state.symbols) >= 2 and not df.empty and not df2.empty:
            st.subheader('Spread & Z-Score (time series)')
            spread, z = compute_spread_zscore(df, df2, hedge_ratio=1.0, window=window)
            # line chart with two axes (spread & zscore)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=spread.index, y=spread.values, name='Spread', line=dict(color='cyan')))
            fig2.add_trace(go.Scatter(x=z.index, y=z.values, name='Z-Score', line=dict(color='magenta'), yaxis='y2'))
            fig2.update_layout(yaxis2=dict(overlaying='y', side='right', title='Z-Score'), template='plotly_dark' if st.session_state.theme=='dark' else 'plotly', height=350)
            st.plotly_chart(fig2, use_container_width=True)
            try:
                png_spread = pio.to_image(fig2, format='png', scale=2)
                st.download_button('Download Spread & Z PNG', data=png_spread, file_name=f'spread_z_{primary}_{secondary}.png', mime='image/png')
            except Exception:
                pass

            # Rolling correlation
            st.subheader('Rolling Correlation')
            rc = rolling_correlation(df, df2, window=corr_window)
            st.line_chart(rc.fillna(0))

            # Kalman hedge ratio
            st.subheader('Dynamic Hedge Ratio (Kalman)')
            hr_ts = compute_hedge_ratio_kalman(df['close'] if 'close' in df.columns else df['price'], df2['close'] if 'close' in df2.columns else df2['price'])
            if len(hr_ts) > 0:
                hr_idx = df['close'].dropna().index[:len(hr_ts)]
                st.line_chart(pd.Series(hr_ts, index=hr_idx))

            # Analysis summary
            st.subheader('Analysis Summary')
            latest_z = float(z.dropna().iloc[-1]) if not z.dropna().empty else None
            latest_corr = float(rc.dropna().iloc[-1]) if not rc.dropna().empty else None
            vol_primary = float(df['close'].pct_change().std()*np.sqrt(252)) if 'close' in df.columns else float(df['price'].pct_change().std()*np.sqrt(252))
            risk = 'Low'
            if latest_z is not None:
                if abs(latest_z) > 2.5: risk = 'High'
                elif abs(latest_z) > 1.5: risk = 'Medium'
            st.write(f"- Latest z-score: {latest_z:.3f}" if latest_z is not None else "- Latest z-score: N/A")
            st.write(f"- Latest rolling correlation: {latest_corr:.3f}" if latest_corr is not None else "- Latest rolling correlation: N/A")
            st.write(f"- Annualized volatility (primary): {vol_primary:.3f}")
            st.markdown(f"**Risk level:** {risk}")
            if latest_z is not None:
                if abs(latest_z) > 2.0:
                    st.warning('Z-score breach — possible mean-reversion opportunity or structural break.')
                else:
                    st.success('Z-score within normal range.')

            # Download spread and zscore CSV
            df_out = pd.DataFrame({'timestamp': spread.index, 'spread': spread.values, 'zscore': z.values})
            csv = df_out.to_csv(index=False)
            st.download_button('Download spread & zscore CSV', data=csv, file_name=f'spread_zscore_{primary}_{secondary}.csv', mime='text/csv')

with cols[1]:
    st.subheader('Quick Stats & Controls')
    # price stats for primary
    if df is not None and not df.empty:
        stats = compute_price_stats(df)
        st.metric('Mean', f"{stats['mean']:.2f}")
        st.metric('Std', f"{stats['std']:.2f}")
        st.metric('Min', f"{stats['min']:.2f}")
        st.metric('Max', f"{stats['max']:.2f}")
    # Alerts
    st.markdown('### Alerts')
    metric = st.selectbox('Metric', ['zscore','spread'])
    op = st.selectbox('Operator', ['>','<'])
    val = st.number_input('Threshold', value=2.0)
    if st.button('Create Alert'):
        a = {'id': len(ALERTS)+1, 'metric': metric, 'op': op, 'value': val, 'symbols': st.session_state.symbols, 'tf': tf, 'window': window, 'hedge_ratio': 1.0}
        add_alert(a); st.success('Alert created. Check console for triggers.')

    st.markdown('### Live tick counts')
    counts = {s: len(tick_storage.get(s, [])) for s in st.session_state.symbols}
    for k,v in counts.items(): st.write(f"{k}: {v}")

    st.markdown('### Replay / Export')
    if st.button('Replay last uploaded NDJSON (simulated)'):
        st.info('Replay started (simulated) - not implemented in this build.')
    if st.button('Download latest resampled CSV'):
        try:
            out = df.reset_index().to_csv(index=False); st.download_button('Download CSV', data=out, file_name=f'{primary}_resampled.csv')
        except Exception as e:
            st.error('No data to download: '+str(e))
