import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller
def compute_price_stats(df):
    s = df['price'] if 'price' in df.columns else df['close']
    return {'mean': float(s.mean()), 'std': float(s.std()), 'min': float(s.min()), 'max': float(s.max())}
def compute_hedge_ratio_ols(df_a, df_b):
    a = df_a['close'] if 'close' in df_a.columns else df_a['price']
    b = df_b['close'] if 'close' in df_b.columns else df_b['price']
    a,b = a.align(b, join='inner')
    if len(a)<2: return {'hedge_ratio':1.0,'r_squared':0.0}
    X = np.vstack([np.ones(len(b)), b]).T
    coeffs = np.linalg.lstsq(X, a.values, rcond=None)[0]
    intercept, slope = coeffs[0], coeffs[1]
    resid = a.values - (intercept + slope*b.values)
    rss = np.sum(resid**2); tss = np.sum((a.values - a.values.mean())**2)
    r2 = 1 - rss/tss if tss!=0 else 0.0
    return {'hedge_ratio': float(slope), 'intercept': float(intercept), 'r_squared':float(r2)}
def compute_spread_zscore(df_a, df_b, hedge_ratio=1.0, window=30):
    a = df_a['close'] if 'close' in df_a.columns else df_a['price']
    b = df_b['close'] if 'close' in df_b.columns else df_b['price']
    a,b = a.align(b, join='inner')
    spread = a - hedge_ratio*b
    z = (spread - spread.rolling(window).mean())/spread.rolling(window).std()
    return spread, z
def run_adf_test(series):
    try:
        res = adfuller(series.dropna())
        return {'adf_stat': float(res[0]), 'pvalue': float(res[1]), 'crit': res[4]}
    except Exception as e:
        return {'adf_stat':0.0, 'pvalue':1.0, 'error':str(e)}
def rolling_correlation(df_a, df_b, window=30):
    a = df_a['close'] if 'close' in df_a.columns else df_a['price']
    b = df_b['close'] if 'close' in df_b.columns else df_b['price']
    a,b = a.align(b, join='inner')
    return a.rolling(window).corr(b)
def compute_hedge_ratio_kalman(y, x):
    y = y.dropna(); x = x.dropna()
    x,y = x.align(y, join='inner')
    n = len(x)
    if n==0: return []
    delta = 1e-5
    Vw = delta/(1-delta)*np.eye(2)
    Ve = 0.001
    beta = np.zeros((2,n))
    P = np.eye(2)
    for t in range(n):
        xt = np.array([1.0, x.iloc[t]])
        if t==0:
            beta[:,t]=0; continue
        R = P + Vw
        yhat = xt.dot(beta[:,t-1])
        e = y.iloc[t] - yhat
        Q = xt.dot(R).dot(xt.T) + Ve
        K = R.dot(xt)/Q
        beta[:,t] = beta[:,t-1] + K*e
        P = R - np.outer(K, xt).dot(R)
    return beta[1,:]
