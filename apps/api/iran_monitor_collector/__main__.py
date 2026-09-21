import json,sys
from pathlib import Path
if len(sys.argv)!=2 or sys.argv[1] != 'build-info': raise SystemExit('usage: python -m iran_monitor_collector build-info')
print(json.dumps(json.loads((Path('/app')/'BUILD_INFO.json').read_text()),sort_keys=True,separators=(',',':')))
