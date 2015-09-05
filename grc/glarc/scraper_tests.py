import unittest
import enlighten_scraper as es
from lxml import html
import lxml
import graph_utils as gu
import networkx as nx
import text_utils as tu
import tfidf

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


class GraphTestCases(unittest.TestCase):
	def test_graph_making(self):
		data_dict = {"123": {
							'title': 'a paper',
							'authors': [('Albert Einstein', "url1"), ("Donald Knuth", "url2"), ("Cristiano Ronaldo", "url3")],
							'abstract': "this paper is about paper",
							"url": 'paperurl123',
							"keywords": [],
							"year": "1977"
							},
					"456": {
							'title': 'another paper',
							'authors': [('Albert Einstein', "url1"), ("Ada Lovelace", "url4")],
							'abstract': "abstractions about abstracts",
							"url": 'paperurl456',
							"keywords": [],
							"year": "1799"
							}
					}

		name_urls = [('Albert Einstein', "url1"), ("Ada Lovelace", "url4")]

		cgm = gu.CollabGraphMaker()
		cgm.populate_graph(data_dict, name_urls)
		graph = cgm.get_graph()

		self.assertEqual(graph.number_of_nodes(), 4)
		self.assertEqual(graph.number_of_edges(), 4)
		self.assertTrue("url1" in graph.nodes() and "url2" in graph.nodes() and "url3" in graph.nodes() and "url4" in graph.nodes())
		self.assertTrue(graph.has_edge("url1", "url2") and graph.has_edge("url1", "url3") and graph.has_edge("url2", "url3") and graph.has_edge("url1", "url4"))
		self.assertTrue(graph.node["url1"]["in_school"] and graph.node["url4"]["in_school"])
		self.assertFalse(graph.node["url2"]["in_school"] and graph.node["url3"]["in_school"])
		self.assertEqual(graph['url1']['url2']["collab_title_url_years"], [['a paper', 'paperurl123', '1977']])
		self.assertEqual(graph.node['url1']['paper_count'], 2)

	def test_sim_graph_making(self):
		akw = {
				1: {"keywords": ["java", "python", "django"]},
				2: {"keywords": ["java", "python", "graphs"]},
				3: {"keywords": ["software", "graphs", "programming"]}
			}

		col_graph = nx.Graph()
		col_graph.add_node(1, {"name": 'bob', 'in_school': True, 'paper_count': 12})
		col_graph.add_node(2, {"name": 'alice', 'in_school': True, 'paper_count': 10})
		col_graph.add_node(3, {"name": 'eve', 'in_school': True, 'paper_count': 20})
		col_graph.add_edge(1, 3)

		sim_graph = gu.make_sim_graph(akw, col_graph)
		self.assertEqual(sim_graph.number_of_nodes(), 3)
		self.assertEqual(sim_graph.number_of_edges(), 2)
		self.assertTrue(sim_graph.has_edge(1, 2) and sim_graph.has_edge(2, 3))
		self.assertTrue("java" in sim_graph[1][2]['sim_kw'] and "python" in sim_graph[1][2]['sim_kw'])
		self.assertTrue("graphs" in sim_graph[2][3]['sim_kw'])


class TextUtilsTests(unittest.TestCase):
	def test_check_sim(self):
		kw1 = ["java", "python", "django"]
		kw2 = ["python", "programming", "django", "graphs"]
		result = tu.check_kw_sim(kw1, kw2)
		self.assertEqual(result[0], 0.5)
		self.assertEqual(result[1], [0, 2])

	def test_get_most_frequent(self):
		words = ['to', 'be', 'or', 'not', 'to', 'be']
		top = tu.get_most_frequent(words, 2)
		self.assertTrue(len(top) == 2)
		self.assertTrue('to' in top and 'be' in top)

class TfidfTests(unittest.TestCase):
	def test_add_text(self):
		tf = tfidf.Tfidf()
		text1 = "the python unit tests python"
		tf.add_text(text1)
		
		expected = {"the":1, "python":1, "unit":1, "tests":1}
		self.assertEqual(tf.get_idf_dict(), expected)

		text2 = "the java unit tests java"
		tf.add_text(text2)

		expected = {"the":2, "python":1, "unit":2, "tests":2, "java":1}
		self.assertEqual(tf.get_idf_dict(), expected)

	def test_count_words(self):
		tf = tfidf.Tfidf()
		text1 = "the python unit tests python"
		expected = {"the":1, "python":2, "unit":1, "tests":1}
		self.assertEqual(tf.count_words(text1), expected)

	def test_get_keywords(self):
		tf = tfidf.Tfidf()
		text1 = "the python unit tests python"	
		tf.add_text(text1)		
		text2 = "the java unit tests java"
		tf.add_text(text2)

		self.assertEqual(tf.get_keywords(text1, 1), ['python'])	


if __name__ == '__main__':
	unittest.main()
