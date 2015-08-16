# Inverted index experimentation
# Using dict but need to think about how to persist this
# TODO refactor, think about how querying will work
# clear up responsibilities between modules/classes

from collections import defaultdict
import json
import shelve
from nltk import stem


class Search(object):
	
	def __init__(self, index_path=None, tkw_path=None):
		#print "in init, index_path is", index_path
		if index_path == None:
			self.index_path = defaultdict(set)
		else:
			self.index_path = index_path
			print "path is", self.index_path
			self.tkw_path = tkw_path
			#she = shelve.open(path)
			#print she["programming"]

	# TODO can record size of postings to optimise intersections - faster if start intersecting with smallest set; 
	# see Intro to IR pg.11
	# TODO also record amount of times author has this term 
	def make_index(self, data_dict=None):
		if data_dict==None:
			with open("../coauthor_data/School of Computing Science.txt") as f:
				data_dict = json.load(f)
		
		for title in data_dict:
			text = title
			abstract = data_dict[title]["abstract"]
			# Some papers do not have an abstract
			if abstract:
				if not isinstance(abstract, basestring):
					text += "\n" + abstract[0]
				else:
					text += "\n" + abstract

			#terms = set(self.process_text(data_dict[title]["keywords"]))
			terms = set(self.process_text(text))
			# Authors is list of lists, we want second element in list (the unique identifier)
			authors = [author[1] for author in data_dict[title]["authors"]]
			# For each keyword term in this paper, add authors to postings set
			for term in terms:
				term = term.encode("utf-8")
				self.index[term].update(authors)


	# TODO is text coming in as a string or a list?
	# Assume string for now, but it will be all separated by spaces by this point
	# CURRENT STATUS kw coming in as a LIST (of PHRASES)
	# NB not making tokens into a set because this same method will be used on query
	# and want to keep query as full phrase with repeated words if the case
	def process_text(self, text):
		prtr = stem.porter.PorterStemmer()
		# Tokenise
		tokens = text.lower().split()
		tokens = [prtr.stem(token) for token in tokens]

		# TODO do stemming, lemmatization etc.. NLTK?

		return tokens

	def get_index(self):
		return self.index

	# TODO do this from outside... From the future django view
	def search(self, query):
		if query[0] == "\"" and query[-1] == "\"":
		# TODO for phrase query, since the full text is small (just the keyword string),
		# do an and_search for the tokens in phrase, then look for full phrase within the
		# keyword string for each of those authors; simple alternative to using a positional index / positional intersect
			pass

		# TODO use regex here to make sure and isn't in middle of word etc etc
		elif 'AND' in query:
			self.and_search(query)
		else:
			self.or_search(query)

	def get_author_sets(self, q):
		
		she = shelve.open(self.index_path)
		
		q = [term.encode("utf-8") for term in self.process_text(q)]
		author_sets = []
		for term in q:
			if term in she:
				#print term
				#print "term in she"
				#print she[term]
				author_sets.append(she[term])
		#result = [she[term] for term in self.process_text(q)]
		she.close()
		return author_sets

	def get_title_sets(self, q):
		data = shelve.open(self.index_path)
		#with open(self.index_path) as f:
		#	data = json.load(f)
		#print "opened json file"
		q = [term.encode("utf-8") for term in self.process_text(q)]
		title_sets = []
		for term in q:
			if term in data:
				#print term
				#print "term in she"
				#print data[term]
				title_sets.append(data[term])
		#result = [she[term] for term in self.process_text(q)]
		data.close()
		#print title_sets
		return title_sets


	# Return authors where each of the query terms is found in at least one of their papers
	# NB query terms do not have to all appear in one paper - the AND is at the author level, not the paper level
	def and_search(self, q):
		title_sets = self.get_title_sets(q)
		#print title_sets
		author_sets = []
		author_papers = []
		tkw_index = shelve.open(self.tkw_path)
		print "opened tkw"
		
		for index, title_set in enumerate(title_sets):
			author_sets.append([])
			for title in title_set:
				title = title.encode("utf-8")
				
				if title in tkw_index:
					url = tkw_index[title]["url"]
					authors = tkw_index[title]["authors"]
					for author in authors:
						author = tuple(author)
						author_sets[index].append(author)
						author_papers.append((author, (title, url)))
			
			author_sets[index] = set(author_sets[index])
			

		tkw_index.close()
		#print author_sets
		matching_authors = set.intersection(*author_sets)
		final_result = [author_paper for author_paper in author_papers if author_paper[0] in matching_authors]
		
		print final_result
		return final_result
			 
		

		#return set.intersection(*self.get_title_sets(q))

	def or_search(self, q):
		print "or searching"
		titles = set.union(*self.get_title_sets(q))
		authors = []
		author_papers = []
		tkw_index = shelve.open(self.tkw_path)
		for title in titles:
			title = title.encode("utf-8")
			url = tkw_index[title]["url"]
			authors = tkw_index[title]["authors"]
			for author in authors:
				author = tuple(author)
				author_papers.append((author, (title, url)))

		#print author_papers
		return author_papers

	# Return authors where the query phrase is present in the keywords of at least one of their papers
	def phrase_search(self, q):
		print "phrase searching"
		#candidates = set.intersection(*self.get_author_sets(q))
		#print candidates
		titles = set.intersection(*self.get_title_sets(q))
		tkw_index = shelve.open(self.tkw_path)
		author_papers = []
		for title in titles:
			title = title.encode("utf-8")
			print "query is", q
			#print "author is", author
			#print "keyword string is", akwindex[author]
			if title in tkw_index:
				if q in "|".join(tkw_index[title]["keywords"]):
					authors = tkw_index[title]["authors"]
					url = tkw_index[title]["url"]
					for author in authors:
						author = tuple(author)
						author_papers.append((author, (title, url)))

		print author_papers
		return author_papers








