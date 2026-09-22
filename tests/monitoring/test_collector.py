import unittest
from unittest.mock import Mock,patch
from urllib.error import URLError
from collector import MAX_BYTES,TIMEOUT,NoRedirect,clean,one_request,parse
from ops import classify

class FeedParsingTests(unittest.TestCase):
    def test_html_summary_sanitized_and_unicode_preserved(self):
        self.assertEqual(clean('<p>خبر فارسی&nbsp;<b>and</b></p><script>leak()</script><iframe>ignored</iframe>'), 'خبر فارسی and')

    def test_rss_description_is_used_without_article_fetch(self):
        xml=b'''<rss><channel><item><title>Missile defense update</title><link>https://example.org/story?utm_source=feed</link><description><![CDATA[&lt;p&gt;Summary &amp;amp; details&lt;/p&gt;]]></description><pubDate>Mon, 21 Sep 2026 12:00:00 +0000</pubDate></item></channel></rss>'''
        items,observed,rejected,_meta=parse(xml,'source-1','2026-09-21T12:01:00+00:00')
        self.assertEqual((observed,rejected),(1,0));self.assertEqual(items[0]['summary_source'],'description')
        self.assertEqual(items[0]['summary_text'],'Summary & details');self.assertNotIn('utm_source',items[0]['canonical_url'])
        self.assertEqual(items[0]['published_at'],'2026-09-21T12:00:00+00:00')

    def test_no_summary_remains_explicitly_unavailable(self):
        xml=b'<rss><channel><item><title>Headline</title><link>https://example.org/story</link></item></channel></rss>'
        item=parse(xml,'s','2026-09-21T12:00:00+00:00')[0][0]
        self.assertIsNone(item['summary_text']);self.assertFalse(item['summary_available'])

    def test_atom_summary_and_canonical_article_link_only(self):
        xml=b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Satellite update</title><link href="https://example.org/a"/><summary type="html">&lt;p&gt;Orbit update&lt;/p&gt;</summary><updated>2026-09-21T12:00:00Z</updated></entry></feed>'''
        items,observed,rejected,_meta=parse(xml,'s','2026-09-21T12:01:00+00:00')
        self.assertEqual((observed,rejected),(1,0));self.assertEqual(items[0]['summary_source'],'atom_summary')
        self.assertEqual(items[0]['summary_text'],'Orbit update')
        self.assertIsNone(items[0]['content_language'])

    def test_only_explicit_feed_language_is_recorded(self):
        xml=b'<rss><channel><language>fa-IR</language><item><title>Headline</title><link>https://example.org/a</link></item></channel></rss>'
        items,_,_,_=parse(xml,'s','2026-09-21T12:00:00+00:00')
        self.assertEqual(items[0]['content_language'],'fa-IR')

    def test_classification_uses_only_observed_text_and_has_no_confidence(self):
        category,topics,matched=classify('Cyber incident response','Negotiations on energy')
        self.assertEqual(category['id'],'cybersecurity');self.assertTrue(topics);self.assertTrue(matched)
        self.assertEqual(classify('Unmatched phrase',None)[0]['id'],'other')

class BoundedNetworkTests(unittest.TestCase):
    def test_one_request_does_not_retry_and_uses_fixed_timeout(self):
        opener=Mock();opener.open.side_effect=URLError('offline')
        with patch('collector.build_opener',return_value=opener):
            status,body,size,started,error=one_request('https://feeds.example.test/rss')
        self.assertIsNone(status);self.assertEqual(body,b'');self.assertEqual(size,0)
        self.assertEqual(error,'URLError');opener.open.assert_called_once()
        self.assertEqual(opener.open.call_args.kwargs['timeout'],TIMEOUT)

    def test_response_limit_stops_at_one_byte_over_cap(self):
        class Response:
            status=200
            def __init__(self):self.remaining=MAX_BYTES+1
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,size):
                n=min(size,self.remaining);self.remaining-=n;return b'x'*n
        opener=Mock();opener.open.return_value=Response()
        with patch('collector.build_opener',return_value=opener):
            status,body,size,started,error=one_request('https://feeds.example.test/rss')
        self.assertIsNone(status);self.assertEqual(body,b'');self.assertEqual(size,0)
        self.assertEqual(error,'ValueError');opener.open.assert_called_once()

    def test_redirects_are_rejected(self):
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'Found',{},'https://other.example/'))

if __name__=='__main__':unittest.main()
