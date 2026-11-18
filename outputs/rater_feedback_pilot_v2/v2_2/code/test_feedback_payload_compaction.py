import unittest
from src.recsaver.feedback_payload_compaction import compact_payload, expand_payload,intern_payload,expand_interned


class PayloadCompactionTest(unittest.TestCase):
    def test_shared_span_lossless_and_conflicts_rejected(self):
        e = dict(span_id='1:1@U001', text='"quoted"\r\n', start=0, end=10)
        p = dict(claims=[dict(evidence=[e]), dict(evidence=[e])], target=dict(text=e['text'], spans=[e]))
        c = compact_payload(p)
        self.assertEqual(expand_payload(c), p)
        self.assertEqual(len(c['_evidence_catalog']), 1)
        self.assertEqual(c['target'], p['target'])
        self.assertEqual(expand_interned(intern_payload(p)),p)
        with self.assertRaises(AssertionError):
            compact_payload(dict(claims=[dict(evidence=[e, dict(e, text='changed')])]))


if __name__ == '__main__':
    unittest.main()
