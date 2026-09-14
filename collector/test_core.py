# offline fixture tests
from iran_monitor_collector.core import *
def test_normalize(): assert normalize_url('HTTP://Example.com/a?utm_x=1&b=2#x')=='http://example.com/a?b=2'
def test_id(): assert stable_item_id('s','https://x/a')==stable_item_id('s','https://x/a')
def test_dedup(): assert len(deduplicate([{'canonical_url':'a'},{'canonical_url':'a'}]))==1
