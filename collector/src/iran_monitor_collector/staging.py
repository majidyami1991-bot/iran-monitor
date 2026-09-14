import os,tempfile,json
class LocalJsonlSink:
 def __init__(self,path): self.path=path
 def write(self,items):
  os.makedirs(os.path.dirname(self.path),exist_ok=True); fd,tmp=tempfile.mkstemp(dir=os.path.dirname(self.path)); os.close(fd)
  with open(tmp,'w') as f:
   for x in items:f.write(json.dumps(x,sort_keys=True)+'\n')
  os.replace(tmp,self.path)
