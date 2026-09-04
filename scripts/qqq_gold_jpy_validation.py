#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

START='2020-07-31'; END='2026-08-31'; COST_BPS=20.0
SYMS=('QQQ','GLD','SPY')

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; investor2-research/1.0; +https://github.com/KAFKA2306/investor2)'})
    with urllib.request.urlopen(req,timeout=45) as r: b=r.read()
    if not b: raise RuntimeError('empty '+url)
    return b

def yahoo(sym):
    p1=int(pd.Timestamp(START,tz='UTC').timestamp()); p2=int((pd.Timestamp(END,tz='UTC')+pd.Timedelta(days=1)).timestamp())
    q=urllib.parse.urlencode({'period1':p1,'period2':p2,'interval':'1d','events':'history','includeAdjustedClose':'true'})
    url=f'https://query1.finance.yahoo.com/v8/finance/chart/{sym}?{q}'; b=get(url); d=json.loads(b)
    n=d['chart']['result'][0]; a=n['indicators']['adjclose'][0]['adjclose']
    s=pd.Series(a,index=pd.to_datetime(n['timestamp'],unit='s',utc=True).tz_convert(None).normalize(),name=sym).dropna().astype(float)
    return s, {'provider':'yahoo_chart','symbol':sym,'url':url,'sha256':hashlib.sha256(b).hexdigest(),'rows':int(len(s)),'start':str(s.index.min().date()),'end':str(s.index.max().date())}

def fed_fx():
    # Federal Reserve H.10 DDP, Japanese Yen (JPY per USD), last 2000 observations.
    url='https://www.federalreserve.gov/datadownload/Output.aspx?rel=H10&series=60f32914ab61dfab590e0e470153e3ae&lastobs=2000&from=&to=&filetype=csv&label=include&layout=seriescolumn&type=package'
    b=get(url); p=Path('/tmp/fx.csv'); p.write_bytes(b)
    raw=pd.read_csv(p)
    date_col=next((c for c in raw.columns if str(c).strip().lower() in ('date','series description')),raw.columns[0])
    # DDP CSV has metadata rows before observations; locate rows whose first field parses as dates.
    dates=pd.to_datetime(raw[date_col],errors='coerce')
    value_cols=[c for c in raw.columns if c!=date_col]
    chosen=None
    for c in value_cols:
        vals=pd.to_numeric(raw[c],errors='coerce')
        mask=dates.notna() & vals.notna()
        if mask.sum()>1000:
            chosen=(c,vals,mask); break
    if chosen is None: raise RuntimeError(f'cannot parse H10 DDP columns={list(raw.columns)} head={raw.head(8).to_dict()}')
    c,vals,mask=chosen
    s=pd.Series(vals[mask].to_numpy(float),index=dates[mask].dt.normalize(),name='JPY_per_USD').sort_index()
    s=s[(s.index>=START)&(s.index<=END)]
    if len(s)<1400: raise RuntimeError(f'only {len(s)} FX rows parsed from {c}')
    return s, {'provider':'Federal Reserve H.10 Data Download Program','series':'H10/H10/RXI_N.B.JA','units':'Japanese Yen per U.S. Dollar','url':url,'sha256':hashlib.sha256(b).hexdigest(),'rows':int(len(s)),'start':str(s.index.min().date()),'end':str(s.index.max().date())}

def strategy(px, target):
    rets=px.pct_change().dropna(); w=np.array(target,dtype=float); values=[]; turnovers=0.0; prev_month=None
    for dt,row in rets.iterrows():
        month=(dt.year,dt.month); cost=0.0
        if prev_month is None: prev_month=month
        elif month!=prev_month:
            # weights drifted through prior close; rebalance before today's close-to-close return
            turnover=float(np.abs(w-np.array(target)).sum()/2.0); turnovers+=turnover; cost=turnover*COST_BPS/10000.0
            w=np.array(target,dtype=float); prev_month=month
        r=float(np.dot(w,row.to_numpy(float))) - cost
        values.append((dt,r))
        gross=w*(1.0+row.to_numpy(float)); w=gross/gross.sum()
    s=pd.Series(dict(values)).sort_index(); return s,turnovers

def metrics(r):
    eq=(1+r).cumprod(); yrs=len(r)/252; cagr=float(eq.iloc[-1]**(1/yrs)-1); vol=float(r.std(ddof=1)*math.sqrt(252)); sharpe=float(r.mean()/r.std(ddof=1)*math.sqrt(252)); dd=eq/eq.cummax()-1; n=max(1,math.ceil(len(r)*0.05)); es=float(r.nsmallest(n).mean())
    return {'observations':len(r),'cagr':cagr,'annualized_volatility':vol,'sharpe':sharpe,'maximum_drawdown':float(dd.min()),'daily_expected_shortfall_95':es,'worst_day':float(r.min()),'total_return':float(eq.iloc[-1]-1)}

def main():
    src=[]; cols=[]
    for s in SYMS:
        x,m=yahoo(s); cols.append(x); src.append(m)
    fx,fm=fed_fx(); src.append(fm)
    usd=pd.concat(cols,axis=1,join='inner').dropna(); common=usd.join(fx,how='inner').dropna()
    if len(common)<1400: raise RuntimeError(f'only {len(common)} common rows')
    jpy=common[list(SYMS)].mul(common['JPY_per_USD'],axis=0)
    configs={'QQQ100':[1,0,0],'QQQ80_GLD20':[.8,.2,0],'QQQ80_SPY20':[.8,0,.2]}
    periods={'full':('2020-08-01','2026-08-31'),'early':('2020-08-01','2023-12-31'),'recent':('2024-01-01','2026-08-31')}
    out={'schema_version':'investor2.qqq-gold-jpy-validation.v1','hypothesis':'For an unhedged JPY investor, QQQ80+GLD20 improves realized tail risk versus QQQ100 and QQQ80+SPY20 across fixed periods while keeping CAGR drag versus QQQ within 3 percentage points.','acceptance':{'all_fixed_periods':['gold MDD >= both benchmarks','gold ES >= both benchmarks','gold vol <= both benchmarks','gold CAGR >= QQQ CAGR - 0.03']},'data':{'asset_currency':'USD','investor_currency':'JPY','fx_contract':'Federal Reserve H.10 JPY per USD exact-date intersection; no fill/interpolation','common_rows':len(common),'common_start':str(common.index.min().date()),'common_end':str(common.index.max().date()),'sources':src},'periods':{}}
    passes=True
    for pn,(a,b) in periods.items():
        p=jpy.loc[a:b]; res={}
        for name,w in configs.items():
            rr,to=strategy(p,w); res[name]={'metrics':metrics(rr),'one_way_turnover':to}
        g=res['QQQ80_GLD20']['metrics']; q=res['QQQ100']['metrics']; sp=res['QQQ80_SPY20']['metrics']
        gates={'mdd':g['maximum_drawdown']>=max(q['maximum_drawdown'],sp['maximum_drawdown']),'es':g['daily_expected_shortfall_95']>=max(q['daily_expected_shortfall_95'],sp['daily_expected_shortfall_95']),'vol':g['annualized_volatility']<=min(q['annualized_volatility'],sp['annualized_volatility']),'cagr_drag':g['cagr']>=q['cagr']-.03}
        passes=passes and all(gates.values()); out['periods'][pn]={'start':a,'end':b,'results':res,'gates':gates}
    out['verdict']='USE' if passes else 'REJECT'; print(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True))
if __name__=='__main__': main()
