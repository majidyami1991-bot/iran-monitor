import json,os,tempfile
class CheckpointStore:
 def __init__(self,path): self.path=path
 def load(self): return json.load(open(self.path)) if os.path.exists(self.path) else {}
 def save(self,state):
  os.makedirs(os.path.dirname(self.path),exist_ok=True); fd,tmp=tempfile.mkstemp(dir=os.path.dirname(self.path)); os.close(fd); open(tmp,'w').write(json.dumps(state,sort_keys=True)); os.replace(tmp,self.path)
 def rollback(self):
  if os.path.exists(self.path): os.remove(self.path)
