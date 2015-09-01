import networkx as nx
from networkx.readwrite import json_graph
import json
import tfidf
import rake
import time
import community
import operator

class GraphMaker(object):

	def __init__(self, g=None):
		#self.data_dict = dd
		self.schl_names = []
		if g==None:
			self.graph = nx.Graph()
		else:
			self.graph = g
		#self.populate_graph()


	def populate_graph(self, data_dict, sn=None):
		self.schl_names = sn

		for paper_id, info in data_dict.items():
			# Check if authors is a list of tuples (data from scraping) or of strings (data from oai)
			# Or use subclasses with different implementations of add_vertices here
			title = info["title"]
			#print "title is " + title.encode("utf-8")
			authors = info["authors"]
			if not authors:
				continue
			
			for author in authors:
				self.add_vertex(author)
			
			paper_url = info['url']
			paper_year = info['year']
			self.add_links(title, paper_url, paper_year, authors)

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
			in_school = self.check_schl_status(vertex_id)
			#print name, in_school
			# G.node returns {node: {attributes}} dictionary, can use this to set new attributes after node is created
			self.graph.node[vertex_id]["in_school"] = in_school


	def add_links(self, title, url, year, authors):
		# Check if authors is a list of collections or just strings
		# If collections, make new list out of element at index 1, which is the unique author url and the node id
		if not isinstance(authors[0], basestring):
			authors = [author[1] for author in authors]

		num_authors = len(authors)
		for i in range(0, num_authors):
			for j in range(i+1, num_authors):
				author1 = authors[i]
				author2 = authors[j]
				# Check if edge already exists, update edge attributes
				if self.graph.has_edge(author1, author2):
					self.graph[author1][author2]["weight"] += 1.0 / num_authors
					self.graph[author1][author2]["num_collabs"] += 1
					self.graph[author1][author2]["collab_title_url_years"].append([title, url, year])
				# If edge is new, add it to the graph, give it initial attributes
				else:
					self.graph.add_edge(author1, author2, {'weight': 1.0 / num_authors, "num_collabs": 1, "collab_title_url_years": [[title, url, year],]})


	def check_schl_status(self, author_id):
		
		if self.schl_names:
			# do name abbreviation here to ensure we get everyone?
			# TODO and lowercase to ensure consistency
			# TODO nb now using url to check school membership, more accurate
			for name_url in self.schl_names:
				if author_id in name_url:
					return True 
			
			return False 

		# If no list of names of school members has been provided (e.g. when data comes from OAI) return false
		# TODO or do something else??
		else:
			return False


	def add_metrics(self, g=None):
		print "getting the metrics..."
		deg_cent = nx.degree_centrality(self.graph)
		close_cent = nx.closeness_centrality(self.graph)
		between_cent = nx.betweenness_centrality(self.graph)
		com = community.best_partition(self.graph)

		sorted_coms = self.get_sorted_multimember_coms(com)

		for vertex in self.graph.node.keys():
			self.graph.node[vertex]["deg_cent"] = deg_cent[vertex]
			self.graph.node[vertex]["close_cent"] = close_cent[vertex]
			self.graph.node[vertex]["between_cent"] = between_cent[vertex]
			if com[vertex] in sorted_coms:
				new_com_num = sorted_coms.index(com[vertex])
				#self.graph.node[vertex]["com"] = com[vertex]
				self.graph.node[vertex]["com"] = new_com_num + 1
			else:
				self.graph.node[vertex]["com"] = False

	def add_just_school_community(self, g=None):
		print "adding just school community"
		school_nodes = [node for node in self.graph.node if self.graph.node[node]["in_school"]]
		just_school_graph = self.graph.subgraph(school_nodes)
		print "JUST SCHOOL GRAPH:"
		print just_school_graph
		print just_school_graph.nodes()
		com = community.best_partition(just_school_graph)

		sorted_coms = self.get_sorted_multimember_coms(com)

		for vertex in just_school_graph.node.keys():
			if com[vertex] in sorted_coms:
				new_com_num = sorted_coms.index(com[vertex])
				self.graph.node[vertex]["school_com"] = new_com_num + 1
			else:
				self.graph.node[vertex]["school_com"] = False


	def get_sorted_multimember_coms(self, com_dict):
		print com_dict
		multimembers = {}
		# TODO instead of this use:
		# for comnum in com_dict.values(), if count(com_num) > 1, add to set
		for author, com_num in com_dict.items():
			if com_num in multimembers:
				multimembers[com_num] = True
			else:
				multimembers[com_num] = False

		multimember_coms = []
		for con_num, is_multimember in multimembers.items():
			if is_multimember:
				multimember_coms.append(con_num)

		sorted_coms = sorted(multimember_coms)
		return sorted_coms

	def add_com_keywords(self, akw, g=None):
		com_keywords = {}
		school_com_keywords = {}
		for author in akw:
			keywords = akw[author]["keywords"]
			keywords = [kw[0] for kw in keywords]
			com_num = self.graph.node[author]["com"]
			# Use get as author may not have school_com
			school_com_num = self.graph.node[author].get("school_com")
			if com_num and com_num not in com_keywords:
				com_keywords[com_num] = keywords
			elif com_num in com_keywords:
				com_keywords[com_num].extend(keywords)


			if school_com_num and school_com_num not in school_com_keywords:
				school_com_keywords[school_com_num] = keywords
			elif school_com_num in school_com_keywords:
				school_com_keywords[school_com_num].extend(keywords)


		self.assign_com_keywords(com_keywords, 'com_keywords')
		self.assign_com_keywords(school_com_keywords, 'school_com_keywords')

	
	def assign_com_keywords(self, comkwdict, attr_name):
		self.graph.graph[attr_name] = []
		for com, keywords in comkwdict.items():
			top_com_words = self.get_most_frequent(keywords, 20)
			print "appending " + attr_name
			print top_com_words
			
			if attr_name in self.graph.graph: 
				self.graph.graph[attr_name].append([com, top_com_words])
			else:
				self.graph.graph[attr_name] = [[com, top_com_words],]



	# TODO put in textutils or something
	def get_most_frequent(self, wordlist, maxwords):
		wordcounts = {}
		for word in wordlist:
			if word not in wordcounts:
				wordcounts[word] = wordlist.count(word)

		topwords = sorted(wordcounts.items(), key=operator.itemgetter(1), reverse=True)
		topwords = [wordscore[0] for wordscore in topwords]
		return topwords[:maxwords]



	def get_graph(self):
		return self.graph

	# TODO change this path later
	def write_to_file(self, path):
		graph_data = json_graph.node_link_data(self.graph)
		with open(path, 'w') as f:
			json.dump(graph_data, f)
