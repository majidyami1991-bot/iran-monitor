import json,glob
from pathlib import Path
m=json.load(open('data/runtime/collector/opencti-mapping-plan/mapping-manifest.json')); spec=json.load(open('config/sources/opencti-mapping-spec.json')); assert m['mutations']==0 and spec['mutations_enabled'] is False; assert not spec['prohibited_types'] is None; print('MAPPING_VALIDATOR=PASS')
