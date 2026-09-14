import ast, unittest
from pathlib import Path
from datetime import date
from collections import Counter
import re
source=ast.parse(Path('apps/api/main.py').read_text(encoding='utf-8'))
class HTTPException(Exception):
 def __init__(self,status_code,detail): self.status_code=status_code
scope=dict(date=date,Counter=Counter,re=re,HTTPException=HTTPException)
for node in source.body:
 if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STOPWORDS' for t in node.targets): exec(compile(ast.Module(body=[node],type_ignores=[]),'main','exec'),scope)
 if isinstance(node,ast.FunctionDef) and node.name in ('items','topic_counts'):
  node.decorator_list=[];exec(compile(ast.Module(body=[node],type_ignores=[]),'main','exec'),scope)
class DefectTests(unittest.TestCase):
 def test_topics(self):
  r=scope['topic_counts']([{'title':'The drone drone 2026 with from https://example.test/word','summary':'كشور کشور'}]);self.assertEqual(r,[{'topic':'drone','count':2},{'topic':'کشور','count':2}])
 def test_determinism(self):
  rows=[{'title':'alpha beta gamma'}]*30;self.assertEqual(scope['topic_counts'](rows),scope['topic_counts'](list(reversed(rows))))
 def test_bad_dates(self):
  for value in ('bad','2026-02-30'):
   with self.assertRaises(HTTPException) as cm: scope['items'](date_from=value)
   self.assertEqual(cm.exception.status_code,422)
 def test_inverted(self):
  with self.assertRaises(HTTPException):scope['items'](date_from='2026-09-15',date_to='2026-09-01')
unittest.main()
