# TODO decouple this from the xml parsing
# e.g. have it receive names from another module
from lxml import etree
import networkx as nx

def make_graph():

	G = nx.Graph()

	for i in range(1, 14):
		tree = etree.parse("xmlfile" + str(i) + ".xml")
		root = tree.getroot()
		#root = etree.fromstring(batch)
		print root

		records = root[2]

		for record in records:
			if len(record) and record[0].get("status") != "deleted":
				header = record[0]
				metadata = record[1]
				info = metadata[0]
				authors = []
				for elem in info:
					if "creator" in elem.tag:
						authors.append(elem.text)

				# Using just first last name, first initial
				authors = [author.split()[0] + " " + author.split()[1][:1] for author in authors]


				for i in range(0, len(authors)):
					author = authors[i]
					for j in range(i+1, len(authors)):
						G.add_edge(author, authors[j])

	return G




