"""Translates the held-out QC set with an EXISTING local model, evaluation
only (no download, no approval change, no DB write). Same pipeline as the
gates: translation_tg.translate_field (salted placeholders, exact restore,
validator v2.1.0).

  tg12b (in the local-AI harness container, Ollama on the host):
    python /harness/translation_qc_translate.py --engine tg12b --out /evidence/phase7/heldout-tg12b.json
  nllb (Windows host, CTranslate2):
    runtime/nmt-venv/Scripts/python.exe scripts/translation_qc_translate.py --engine nllb \
        --model-dir runtime/nmt-models/nllb-ct2-int8 --out runtime/local-ai-evidence/phase7/heldout-nllb.json
"""
import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from translation_qc_heldout import HELDOUT  # noqa: E402

TG12B_APPROVAL = 'translategemma-12b-ollama0401-llamacpp-3189e9a01b8a'


def tg12b_call():
    """Identity-verified call into the rejected-but-attested 12B artifact.
    The approval record is read for identity only; its state is not used or
    changed (it stays rejected_quality_gate)."""
    from urllib.request import ProxyHandler, Request, build_opener
    import local_ai
    import model_identity as mi
    import translation_tg as tg
    appr = next(a for a in mi.load_contract()['approvals'] if a['id'] == TG12B_APPROVAL)
    base = local_ai.load_settings().base_url
    rt = appr['runtime']
    facts = mi.verify(appr, base, {'temperature': rt['temperature'], 'num_ctx': rt['num_ctx'], 'num_thread': rt['num_thread'],
                                   'seed': rt['seed'], 'translation_max': rt['translation_max_output_tokens']})
    opener = build_opener(ProxyHandler({}))

    def call(text, num_predict):
        body = tg.request_body(appr['tag'], text, seed=rt['seed'], num_ctx=rt['num_ctx'], num_thread=rt['num_thread'],
                               temperature=rt['temperature'], num_predict=num_predict)
        with opener.open(Request(base + '/api/chat', json.dumps(body, ensure_ascii=False).encode(),
                                 {'Content-Type': 'application/json'}), timeout=900) as r:
            out = json.loads(r.read())
        if out.get('model') != appr['tag']:
            raise RuntimeError('model_identity_mismatch')
        if out.get('done_reason') == 'length':
            raise RuntimeError('output_truncated')
        mi.check_loaded(appr, base)
        return out['message']['content'], out.get('prompt_eval_count'), out.get('eval_count')
    return call, {'approval': appr['id'], 'state_unchanged': True, 'fingerprint': facts['fingerprint'], 'tag': appr['tag'],
                  'manifest_digest': appr['manifest_digest']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--engine', choices=['tg12b', 'nllb'], required=True)
    ap.add_argument('--model-dir')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    if a.engine == 'tg12b':
        import translation_tg as tg
        call, ident = tg12b_call()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location('nmtgate', HERE / 'translation_nmt_gate.py')
        g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(g)  # also installs the psycopg stub (no DB)
        tg = g.tg
        eng = g.CT2Engine('nllb', a.model_dir, 8, 'int8', 4)

        def call(text, num_predict):
            outs, tin, tout = eng.translate(g.split_sentences(text))
            return ' '.join(outs), tin, tout
        ident = {'engine': eng.name, 'runtime': eng.version, 'model_bin_sha256': g.model_identity(a.model_dir)['model.bin']['sha256']}
    rep = {'engine': a.engine, 'identity': ident, 'started': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'items': {}}
    for hid, topic, text in HELDOUT:
        r = tg.translate_field(call, text)
        rep['items'][hid] = {'topic': topic, 'source': text, 'output': r.get('text'), 'validator_status': r['status'],
                             'validator_flags': r.get('flags'), 'latency_ms': r.get('latency_ms')}
        print(hid, r['status'], r.get('latency_ms'), flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(rep, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
