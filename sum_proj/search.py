# Inverted index experimentation
# Using dict but need to think about how to persist this
# TODO refactor, think about how querying will work
# clear up responsibilities between modules/classes

from collections import defaultdict
import json
import shelve
from nltk import stem

class Search(object):
	
	def __init__(self, index_path=None):
		print "BLALSDF"
		if index_path == None:
			self.index = defaultdict(set)
		else:
			self.index = shelve.open(index_path)

	# TODO can record size of postings to optimise intersections - faster if start intersecting with smallest set; 
	# see Intro to IR pg.11
	# TODO also record amount of times author has this term 
	def make_index(self, data_dict=None):
		if data_dict==None:
			with open("../coauthor_data/School of Computing Science.txt") as f:
				data_dict = json.load(f)
		
		for title in data_dict:
			#text = title
			#abstract = data_dict[title]["abstract"]
			# Some papers do not have an abstract
			#if abstract:
			#	if not isinstance(abstract, basestring):
			#		text += "\n" + abstract[0]
			#	else:
			#		text += "\n" + abstract

			terms = set(self.process_text(" ".join(data_dict[title]["keywords"])))
			#terms = set(self.process_text(text))
			# Authors is list of lists, we want second element in list (the unique identifier)
			authors = [author[1] for author in data_dict[title]["authors"]]
			#authors = [(author[0], author[1]) for author in data_dict[title]["authors"]]
			# For each keyword term in this paper, add authors to postings set
			if "java" in terms:
				print title
			for term in terms:
				term = term.encode("utf-8")
				#self.index[term].update(authors)
				self.index[term].add(title)


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


	def make_author_kw_index(self, data_dict=None):
		akw_index = {}
		for title in data_dict:
			kw_string = "|".join(data_dict[title]["keywords"])
			for author in data_dict[title]["authors"]:
				authorid = author[1].encode("utf-8")
				if authorid in akw_index:
					akw_index[authorid] += kw_string + "|"
				else:
					akw_index[authorid] = kw_string + "|"

		return akw_index

	def make_title_kw_index(self, data_dict=None):
		#titles = [title.encode("utf-8") for title in data_dict.keys()]
		tkw = {}
		for paper_id, info in data_dict.items():
			paper_id = paper_id.encode("utf-8")
			del info["abstract"]
			tkw[paper_id] = info

		return tkw

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








