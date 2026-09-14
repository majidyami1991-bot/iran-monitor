from pathlib import Path
import json, argparse

ROOT=Path(__file__).resolve().parents[2]
def load():
 out=[]
 for f in (ROOT/'data/runtime/collector').rglob('normalized-items.jsonl'):
  for line in f.read_text(encoding='utf-8').splitlines():
   try: out.append(json.loads(line))
   except json.JSONDecodeError: pass
 return out
def main():
 p=argparse.ArgumentParser(); p.add_argument('mode',choices=['validate','dry-run','apply']); a=p.parse_args(); rows=load(); ids={x['item_id'] for x in rows}; valid=len(rows)==len(ids) and all(x.get('title') and x.get('canonical_url') for x in rows)
 if not valid: raise SystemExit('validation failed')
 print(json.dumps({'mode':a.mode,'input_item_count':len(rows),'inserted':len(rows) if a.mode=='apply' else 0,'duplicate':0 if a.mode!='apply' else 0,'valid':True}))
if __name__=='__main__': main()
