"""Converts the verified source checkpoints to CTranslate2 int8 models
(one-time; the gate then needs only ctranslate2 + tokenizers). Refuses to run
unless nmt-fetch.json shows every pinned hash matched. NLLB's checkpoint is a
pickle (pytorch_model.bin): torch >= 2.6 loads it with weights_only=True, so
no arbitrary code from the file is executed.

  runtime/nmt-venv/Scripts/python.exe scripts/nmt_convert_models.py
"""
import json
import shutil
import sys
import time
from pathlib import Path

import ctranslate2
import torch
from ctranslate2.converters import TransformersConverter

BASE = Path(__file__).resolve().parents[1] / 'runtime'
fetch = json.loads((BASE / 'local-ai-evidence' / 'phase6' / 'nmt-fetch.json').read_text())
assert all(f['match'] for r in fetch.values() for f in r['files'].values()), 'hash verification failed; not converting'
assert tuple(int(x) for x in torch.__version__.split('+')[0].split('.')[:2]) >= (2, 6), 'torch < 2.6 would unpickle unsafely'

JOBS = [('madlad400-3b-mt', 'madlad-ct2-int8'), ('nllb-200-distilled-600M', 'nllb-ct2-int8')]
log = {}
for src, dst in JOBS:
    s, d = BASE / 'nmt-models' / 'src' / src, BASE / 'nmt-models' / dst
    if d.exists():
        print('exists, skipping', d); continue
    t0 = time.time()
    TransformersConverter(str(s), copy_files=['tokenizer.json'], low_cpu_mem_usage=True).convert(str(d), quantization='int8')
    log[dst] = {'source': str(s), 'seconds': int(time.time() - t0), 'ctranslate2': ctranslate2.__version__, 'torch': torch.__version__,
                'files': {p.name: p.stat().st_size for p in d.iterdir()}}
    print(dst, log[dst], flush=True)
(BASE / 'local-ai-evidence' / 'phase6' / 'nmt-convert.json').write_text(json.dumps(log, indent=2))
