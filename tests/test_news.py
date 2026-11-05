import unittest

from fibermap.news import parse_rss

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>q - Google News</title>
<item><title>AT&amp;T Fiber reaches more of San Diego - AT&amp;T Newsroom</title>
<link>https://news.google.com/rss/articles/abc</link>
<pubDate>Tue, 04 Nov 2026 15:02:00 GMT</pubDate>
<source url="https://about.att.com">AT&amp;T Newsroom</source></item>
<item><title>No source item</title><link>https://example.com/x</link></item>
<item><title></title><link>https://example.com/empty</link></item>
</channel></rss>"""


class NewsTests(unittest.TestCase):
    def test_parse_rss(self):
        items = parse_rss(RSS)
        self.assertEqual(len(items), 2)
        first = items[0]
        self.assertEqual(first["title"], "AT&T Fiber reaches more of San Diego")
        self.assertEqual(first["source"], "AT&T Newsroom")
        self.assertEqual(first["published"], "2026-11-04T15:02:00Z")
        self.assertEqual(items[1]["published"], None)


if __name__ == "__main__":
    unittest.main()
