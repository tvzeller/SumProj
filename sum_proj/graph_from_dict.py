import networkx as nx
from networkx.readwrite import json_graph
import json
import tfidf
import rake

class GraphMaker(object):

	def __init__(self, dd, sn=None):
		self.data_dict = dd
		self.schl_names = [n.lower() for n in sn]
		self.graph = nx.Graph()
		#self.add_kw_to_data()
		#self.harmonise_names()
		#self.populate_graph()


	
	# Paper may or may not have keywords (some Enlighten papers have keywords)
	# If they don't, extract keywords and add to data dict
	# N.B. using rake but could use something else here (e.g. TFIDF)
	def add_kw_to_data(self):
		#ex = tfidf.Extractor()
		
		# for title in self.data_dict:
		# 	text = self.get_text(title)
		# 	ex.add_text(text)

		rk = rake.Rake()
		rk.add_stopwords("stopwords.txt")

		for title, info in self.data_dict.items():
			# If paper does not already have associated keywords
			if not info["keywords"]:
				text = self.get_text(title)
				# rk returns keywords as a list
				# join on "|" and set as keywords for this paper
				# TODO nb we have keywords as string to allow for phrase search (search for substring in keyword string)
				keywords = rk.get_keyphrases(text)
				self.data_dict[title]["keywords"] = keywords
			# If it does, join the list that came from the scraper into string and set as keywords
			#else:
			#	self.data_dict[title]["keywords"] = info["keywords"])

		return self.data_dict

	def get_text(self, title):
		text = title
		abstract = self.data_dict[title]["abstract"]
		# Some papers do not have an abstract
		if abstract:
			text += "\n" + abstract
		
		return text



	# Do this step before passing the data to here - this module should not have to handle this
	# def harmonise_names(self):
	# 	if self.schl_names:
	# 		self.schl_names = [(name.split(", ")[1] + " " + name.split(", ")[0]).lower() for name in self.schl_names]
		
	# 	for title, authors in self.data_dict.items():
	# 		authors = [author.split(", ")[1] + " " + author.split(", ")[0] for author in authors]
	# 		self.data_dict[title] = authors

	def populate_graph(self):
		for title, info in self.data_dict.items():
			# Check if authors is a list of tuples (data from scraping) or of strings (data from oai)
			# Or use subclasses with different implementations of add_vertices here
			print "title is " + title.encode("utf-8")
			authors = info["authors"]
			if not authors:
				continue
			
			for author in authors:
				self.add_vertex(author)
			
			self.add_links(title, authors)

	# TODO consider using polymorphism here... having separate classes for data from scraper vs from oai
	def add_vertex(self, author):
		# author is either a (name, unique_url) pair or just a name string
		# If just a string, the name is used as both the node identifier and the "name" attribute
		# Otherwise access the (name, url) collection to get the url (to use as id) and the author name
		if isinstance(author, basestring):
			print "author is just a string!"
			vertex_id = author
			name = author
		else:
			vertex_id = author[1]
			#print "vertex id is ", vertex_id
			name = author[0]

		# TODO think graph.node can be replaced by just self.graph (also a dict)
		if vertex_id in self.graph.node:
			self.graph.node[vertex_id]["paper_count"] += 1
			# TODO now treating keywords as a string rather than list (concatenate rather than extend)
			#self.graph.node[vertex_id]["keywords"] += " " + keywords
		else:
			#self.graph.add_node(vertex_id, {"name": name, "paper_count": 1, "keywords": keywords})
			# TODO keywords do not go in this graph anymore
			self.graph.add_node(vertex_id, {"name": name, "paper_count": 1})
			in_school = self.check_schl_status(name)
			#print name, in_school
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[vertex_id]["in_school"] = in_school


	def add_links(self, title, authors):
		# Check if authors is a list of collections or just strings
		# If collections, make new list out of element at index 1, which is the unique author url and the node id
		if not isinstance(authors[0], basestring):
			authors = [author[1] for author in authors]

		for i in range(0, len(authors)):
			for j in range(i+1, len(authors)):
				author1 = authors[i]
				author2 = authors[j]
				# Check if edge already exists, update edge attributes
				if self.graph.has_edge(author1, author2):
					self.graph[author1][author2]["num_collabs"] += 1
					self.graph[author1][author2]["collab_titles"].append(title)
				# If edge is new, add it to the graph, give it initial attributes
				else:
					self.graph.add_edge(author1, author2, {'num_collabs': 1, "collab_titles": [title,]})


	def check_schl_status(self, name):
		
		if self.schl_names:
			# do name abbreviation here to ensure we get everyone?
			# TODO and lowercase to ensure consistency
			return name.lower() in self.schl_names

		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		# TODO or do something else??
		else:
			return False

	
	def get_graph(self):
		return self.graph


	def write_to_file(self, filename):
		graph_data = json_graph.node_link_data(self.graph)
		with open("../d3/" + filename + ".json", 'w') as f:
			json.dump(graph_data, f)
