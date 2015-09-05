import unittest
import enlighten_scraper as es
from lxml import html
import lxml

class ScraperTestCases(unittest.TestCase):
	def test_get_name_url_matches(self):
		with open("../scrapertestpages/authorlist.txt") as f:
			text = f.read()

		name = "Williamson, Dr John"
		tree = html.fromstring(text)
		expected = [("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8069.html"), ("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8165.html")]
		#name_urls = es.get_name_url_matches(name, tree)
		self.assertEqual(es.get_name_url_matches(name, tree), expected)

	def test_get_dates_for_papers(self):
		with open("../scrapertestpages/authorpage.txt") as f:
			text = f.read()

		tree = html.fromstring(text)
		expected = ['2015','2014', '2014', '2014']
		self.assertEqual(es.get_dates_for_papers(tree), expected)

	

if __name__ == '__main__':
	unittest.main()
