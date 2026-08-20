from pathlib import Path
import json, hashlib, datetime

OUT = Path(__file__).resolve().parent
KB_FILE = OUT / 'MLAI_CANDLE_LANGUAGE_KB_V1.json'
INDEX_FILE = OUT / 'MLAI_CANDLE_LANGUAGE_INDEX_V1.json'

SOURCES = [
    {'id':'NISON_2001','title':'Japanese Candlestick Charting Techniques, Second Edition','author':'Steve Nison','role':'candlestick interpretation'},
    {'id':'BULKOWSKI_2008','title':'Encyclopedia of Candlestick Charts','author':'Thomas N. Bulkowski','role':'candlestick identification and statistical behavior'},
    {'id':'MURPHY_1999','title':'Technical Analysis of the Financial Markets','author':'John J. Murphy','role':'trend, chart patterns, volume, support/resistance and technical analysis'},
    {'id':'WILDER_1978','title':'New Concepts in Technical Trading Systems','author':'J. Welles Wilder Jr.','role':'RSI, ATR and directional/momentum concepts'},
    {'id':'BOLLINGER_2001','title':'Bollinger on Bollinger Bands','author':'John Bollinger','role':'Bollinger Bands and volatility-aware interpretation'},
]

KB = {
 'schema_version':'1.0',
 'purpose':'Book-grounded market-language knowledge. Descriptive and probabilistic; never an automatic trading command.',
 'sources': SOURCES,
 'rules': [
   {'id':'R001','topic':'causality','machine':'completed_candles_only','human':'Do not interpret an unfinished candle as a completed candle. A 5-minute candle still forming is excluded until its close.','sources':['NISON_2001','MURPHY_1999']},
   {'id':'R002','topic':'candle_anatomy','machine':'long_upper_wick','human':'Price reached materially higher levels but closed lower; this can indicate rejection of higher prices. Context is required.','sources':['NISON_2001','BULKOWSKI_2008']},
   {'id':'R003','topic':'candle_anatomy','machine':'long_lower_wick','human':'Price reached materially lower levels but closed higher; this can indicate rejection of lower prices. Context is required.','sources':['NISON_2001','BULKOWSKI_2008']},
   {'id':'R004','topic':'candle_anatomy','machine':'large_body','human':'The candle produced relatively large net displacement. Compare it with recent candles and volatility before calling it strong.','sources':['NISON_2001','BULKOWSKI_2008']},
   {'id':'R005','topic':'candle_anatomy','machine':'small_body','human':'The candle produced limited net displacement. It may represent hesitation, compression or balanced two-sided movement depending on its wicks and context.','sources':['NISON_2001','BULKOWSKI_2008']},
   {'id':'R006','topic':'candle_anatomy','machine':'two_sided_rejection','human':'Small net change combined with meaningful upper and lower excursions indicates substantial two-sided exploration.','sources':['NISON_2001','BULKOWSKI_2008']},
   {'id':'R007','topic':'volume','machine':'volume_is_participation_proxy','human':'Recorded volume describes activity/participation. It does not directly reveal the exact number of buyers versus sellers or hidden orders.','sources':['MURPHY_1999','NISON_2001']},
   {'id':'R008','topic':'support_resistance','machine':'reaction_area','human':'Support and resistance should be represented as areas derived from prior reactions, swings, highs/lows, breakouts and retests rather than magical exact prices.','sources':['MURPHY_1999']},
   {'id':'R009','topic':'structure','machine':'uptrend','human':'A sequence of higher structural highs and lows can describe an uptrend; the definition must use causal confirmed swings.','sources':['MURPHY_1999']},
   {'id':'R010','topic':'structure','machine':'downtrend','human':'A sequence of lower structural highs and lows can describe a downtrend; the definition must use causal confirmed swings.','sources':['MURPHY_1999']},
   {'id':'R011','topic':'structure','machine':'consolidation','human':'Repeated two-sided movement inside a bounded area with weak directional progression can describe consolidation/range behavior.','sources':['MURPHY_1999']},
   {'id':'R012','topic':'RSI','machine':'rsi_momentum','human':'RSI summarizes recent upward versus downward price momentum. High or low RSI alone is not proof of reversal.','sources':['WILDER_1978']},
   {'id':'R013','topic':'bollinger','machine':'bandwidth_contraction','human':'Narrow Bollinger Band width describes reduced recent volatility; it is a volatility state, not an automatic breakout direction.','sources':['BOLLINGER_2001']},
   {'id':'R014','topic':'bollinger','machine':'band_location','human':'Location near an upper or lower band is relative to the volatility envelope and is not automatically bearish or bullish.','sources':['BOLLINGER_2001']},
   {'id':'R015','topic':'patterns','machine':'named_pattern_is_description','human':'Hammer, engulfing, doji, double top, head-and-shoulders and similar names describe observed geometry/sequences. They do not automatically mean BUY or SELL.','sources':['NISON_2001','BULKOWSKI_2008','MURPHY_1999']},
   {'id':'R016','topic':'prediction','machine':'historical_evidence_is_not_certainty','human':'Historical similarity can change the probability of scenarios but never guarantees the next move.','sources':['BULKOWSKI_2008','MURPHY_1999']},
 ],
 'candle_fields': {
   'body':'abs(close-open)',
   'range':'high-low',
   'upper_wick':'high-max(open,close)',
   'lower_wick':'min(open,close)-low',
   'body_to_range':'body/range when range>0',
   'upper_wick_to_body':'upper_wick/body when body>0',
   'lower_wick_to_body':'lower_wick/body when body>0',
   'close_position':'(close-low)/(high-low) when range>0'
 },
 'sequence_states':['selling','buying','selling_slowing','buying_slowing','rejection','recovery','pullback','retracement','momentum_loss','exhaustion','consolidation','compression','expansion','breakout_candidate','failed_breakout','retest','continuation','transition','reversal_candidate'],
 'pattern_names':['Doji','Hammer','Hanging Man','Inverted Hammer','Shooting Star','Bullish Engulfing','Bearish Engulfing','Harami','Morning Star','Evening Star','Three White Soldiers','Three Black Crows','Piercing Pattern','Dark Cloud Cover','Double Top','Double Bottom','Head and Shoulders','Inverse Head and Shoulders','Triangle','Rectangle','Flag','Pennant','Channel'],
 'indicators':['volume','support_resistance','RSI','Bollinger Bands','ATR','market_structure','candlestick_patterns'],
 'statuses':['candidate','under_evaluation','validated','weak_evidence','failed','deprecated']
}

KB_FILE.write_text(json.dumps(KB,indent=2,ensure_ascii=False),encoding='utf-8')
sha=hashlib.sha256(KB_FILE.read_bytes()).hexdigest()
INDEX_FILE.write_text(json.dumps({'knowledge_base':'MLAI Candle Language KB V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'record_count':len(KB['rules']),'sha256':sha,'source_count':len(SOURCES),'topics':sorted(set(r['topic'] for r in KB['rules']))},indent=2),encoding='utf-8')
print('KB CREATED')
print(KB_FILE)
print(INDEX_FILE)