# Inverted index experimentation
# Using dict but need to think about how to persist this
# TODO refactor, think about how querying will work
# clear up responsibilities between modules/classes

from collections import defaultdict

class Search(object):
	
	def __init__(self):
		self.index = defaultdict(set)

	# TODO can record size of postings to optimise intersections - faster if start intersecting with smallest set; 
	# see Intro to IR pg.11 
	def make_index(self, data_dict):
		for title in data_dict:
			terms = set(self.process_text(data_dict[title]["keywords"]))
			# Authors is list of lists, we want second element in list (the unique identifier)
			authors = [author[1] for author in data_dict[title]["authors"]]
			# For each keyword term in this paper, add authors to postings set
			for term in terms:
				self.index[term].update(authors)


	# TODO is text coming in as a string or a list?
	# Assume string for now, but it will be all separated by spaces by this point
	# NB not making tokens into a set because this same method will be used on query
	# and want to keep query as full phrase with repeated words if the case
	def process_text(self, text):
		# Tokenise
		tokens = text.lower().split()
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
		return [self.index[term] for term in self.process_text(q)]

	def and_search(self, q):
		return set.intersection(*self.get_author_sets(q))

	def or_search(self, q):
		return set.union(*self.get_author_sets(q))








