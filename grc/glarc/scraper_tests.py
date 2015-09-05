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

	def test_initialise(self):
		name = "Poet, Dr Ronald"
		expected = "Poet, Dr R"
		self.assertEqual(es.initialise_first_name(name), expected)

	def test_get_paper_authors(self):
		with open("../scrapertestpages/paperpage.txt") as f:
			text = f.read()

		tree = html.fromstring(text)
		base_url = "http://eprints.gla.ac.uk/view/author/"
		expected = [("Singer, Dr Jeremy", base_url+'15034.html'), ("Alexander, Dr Marc", base_url+"9679.html"), ("Cameron, Mr Callum", base_url+"31163.html")]
		self.assertEqual(es.get_paper_authors(tree), expected)

	def test_get_paper_abstract(self):
		with open("../scrapertestpages/paperpage.txt") as f:
			text = f.read()

		tree = html.fromstring(text)
		expected = "Feature-creep is a well-known phenomenon in software systems. In this paper, we argue that feature-creep also occurs in the domain of programming languages. Recent languages are more expressive than earlier languages. However recent languages generally extend rather than replace the syntax (sometimes) and semantics (almost always) of earlier languages. We demonstrate this trend of agglomeration in a sequence of languages comprising Pascal, C, Java, and Scala. These are all block-structured Algol-derived languages, with earlier languages providing explicit inspiration for later ones. We present empirical evidence from several language-specific sources, including grammar definitions and canonical manuals. The evidence suggests that there is a trend of increasing complexity in modern languages that have evolved from earlier languages."
		self.assertEqual(es.get_paper_abstract(tree), expected)

	def test_get_paper_keywords(self):
		with open("../scrapertestpages/paperpage2.txt") as f:
			text = f.read()	

		tree = html.fromstring(text)
		expected = ['audio icons', 'crossmodal interaction', 'non-visual interaction', 'tactile icons']
		self.assertEqual(es.get_paper_keywords(tree), expected)	


if __name__ == '__main__':
	unittest.main()
