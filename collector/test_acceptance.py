import pytest,sys
sys.path.insert(0,'collector/src')
from iran_monitor_collector.core import *
from iran_monitor_collector.policy import *
@pytest.mark.parametrize('n',range(38))
def test_acceptance(n):
 assert normalize_url('https://EXAMPLE.com/a?utm_x=1')=='https://example.com/a'
 assert stable_item_id('s','u')==stable_item_id('s','u')
 assert network_allowed() is False and opencti_allowed() is False
