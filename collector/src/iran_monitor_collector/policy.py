def network_allowed(): return False
def opencti_allowed(): return False
def require_network(): raise RuntimeError('NETWORK_DISABLED_NOT_APPROVED')
class OpenCTIDisabledSink:
 def write(self,*a,**k): raise RuntimeError('OPENCTI_SINK_DISABLED_NOT_APPROVED')
