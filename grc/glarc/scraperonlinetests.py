import unittest
import enlighten_scraper as es
	

# TODO 
class OnlineScraperTests(unittest.TestCase):
	def test_check_if_in_dept(self):
		author_url = "http://eprints.gla.ac.uk/view/author/9129.html"
		school = "School of Computing Science"
		self.assertTrue(es.check_if_in_dept(author_url, school))

	def test_sort_name_urls(self):
		name_urls = [("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8069.html"), ("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8165.html")]
		school = "School of Computing Science"
		sorted_name_urls = es.sort_name_urls(name_urls, school)
		self.assertTrue(sorted_name_urls[0][0] == ("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8165.html"))

	def test_get_winning_url(self):
		name_urls = [("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8069.html"), ("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8165.html")]
		school = "School of Computing Science"
		expected = ("Williamson, Dr John", "http://eprints.gla.ac.uk/view/author/8165.html")
		self.assertEquals(es.get_winning_url(name_urls, school), expected)

	def test_get_papers_info(self):
		self.maxDiff = None
		author_url = "http://eprints.gla.ac.uk/view/author/26556.html"
		expected = {
					"108933": {
								'title': "Formalising responsibility modelling for automatic analysis.",
								'authors': [("Simpson, Mr Robert", "http://eprints.gla.ac.uk/view/author/26556.html"), ("Storer, Dr Timothy", "http://eprints.gla.ac.uk/view/author/13378.html")],
								'abstract': "Modelling the structure of social-technical systems as a basis for informing software system design is a difficult compromise. Formal methods struggle to capture the scale and complexity of the heterogeneous organisations that use technical systems. Conversely, informal approaches lack the rigour needed to inform the software design and\nconstruction process or enable automated analysis.\nWe revisit the concept of responsibility modelling, which models social technical systems as a collection of actors who discharge their responsibilities, whilst using and producing resources in the process. Responsibility modelling is formalised as a structured approach for socio-technical system requirements specification and modelling, with well-defined semantics and support for automated structure and validity analysis. The\neffectiveness of the approach is demonstrated by two case studies of software engineering methodologies.",
								'url': "http://eprints.gla.ac.uk/108933/",
								'keywords': [],
								'year': "2015"
								}

					}
		self.assertEquals(es.get_papers_info(author_url, []), expected)



if __name__ == '__main__':
	unittest.main()
