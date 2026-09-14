from bs4 import BeautifulSoup
def parse_html(data,base_url='https://example.test/'):
 s=BeautifulSoup(data,'html.parser'); return [{'title':a.get_text(' ',strip=True),'canonical_url':a.get('href')} for a in s.select('article a, h2 a, h3 a')]
def fetch(*a,**k): raise RuntimeError('LIVE_NETWORK_NOT_APPROVED')
