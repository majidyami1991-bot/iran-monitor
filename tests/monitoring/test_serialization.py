import dataclasses, datetime, json, math, os, unittest
from decimal import Decimal
from enum import Enum
from uuid import UUID
from ops import to_json_compatible, canonical_json_dumps, database_json

class Kind(Enum): VALUE='ok'
@dataclasses.dataclass
class Nested: when: datetime.datetime

class SerializationTests(unittest.TestCase):
    def test_temporal_recursive_and_canonical(self):
        aware=datetime.datetime(2026,3,8,1,30,tzinfo=datetime.timezone(datetime.timedelta(hours=-8)))
        value={'d':datetime.date(2026,3,8),'items':[aware], 'nested':Nested(aware), 'uuid':UUID('ABCDEFAB-CDEF-ABCD-EFAB-CDEFABCDEFAB'),'decimal':Decimal('1.2300'),'enum':Kind.VALUE}
        out=to_json_compatible(value,path='payload')
        self.assertEqual(out['items'][0],'2026-03-08T09:30:00Z'); self.assertEqual(out['nested']['when'],out['items'][0]); self.assertEqual(out['uuid'],'abcdefab-cdef-abcd-efab-cdefabcdefab'); self.assertEqual(out['decimal'],'1.2300')
        self.assertEqual(canonical_json_dumps({'when':aware}),canonical_json_dumps({'when':datetime.datetime(2026,3,8,9,30,tzinfo=datetime.timezone.utc)}))
    def test_rejects_ambiguous_and_unknown_values_with_path(self):
        with self.assertRaisesRegex(TypeError,'payload.when:naive_datetime'):to_json_compatible({'when':datetime.datetime(2026,1,1)},path='payload')
        with self.assertRaisesRegex(TypeError,'payload.bytes:bytes'):to_json_compatible({'bytes':b'x'},path='payload')
        with self.assertRaisesRegex(TypeError,'payload.value:non_finite_float'):to_json_compatible({'value':math.nan},path='payload')
    def test_database_json_is_schema_preserving(self):
        value=database_json({'received_at':datetime.datetime(2026,1,1,tzinfo=datetime.timezone.utc),'topics':['a',None]},path='provenance_payload')
        self.assertEqual(json.loads(json.dumps(value))['received_at'],'2026-01-01T00:00:00Z')

if __name__=='__main__':unittest.main()
