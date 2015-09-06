# Module used to support searching for terms within the application.
# Used within the Django views.

from collections import defaultdict
import json
import shelve
from nltk import stem
import text_utils as tu


class Search(object):
	"""
	Search class to deal with keyword searching. Uses indices stored in shelve objects at paths provided.
	"""
	
	def __init__(self, index_path=None, pkw_path=None):
		self.index = shelve.open(index_path)
		self.pkw_index = shelve.open(pkw_path)


	def get_paper_sets(self, q):
		# Get individual and processed terms in query
		q = [term.encode("utf-8") for term in tu.process_text(q)]
		paper_sets = []
		# Get the postings list of paper ids for each term and add to outer list
		for term in q:
			if term in self.index:
				paper_sets.append(self.index[term])

		self.index.close()

		return paper_sets


	def and_search(self, q):
		"""
		Return authors where each of the query terms in q is found in at least one of their papers
		NB query terms do not have to all appear in one paper - the AND is at the author level, not the paper level
		Result in form of {author: list of papers (title, url, year of papers)} dict
		"""

		# Get the postings lists for the query
		paper_sets = self.get_paper_sets(q)
		author_sets = []
		# A dict mapping author ids to their papers which contain the query term
		author_papers = {}
		# Open index mapping paper titles to authors and keywords
		#pkw_index = shelve.open(self.pkw_path)
		# For each postings list
		for index, paper_set in enumerate(paper_sets):
			# Add empty set to list of author_sets
			author_sets.append(set())
			for paper_id in paper_set:
				# For each paper, add the paper's info to the results (author_papers)
				paper_id = paper_id.encode("utf-8")			
				if paper_id in self.pkw_index:
					self.add_authors_to_results(author_papers, self.pkw_index, paper_id, author_sets, index)
					
		self.pkw_index.close()

		matching_authors = set()
		# Get intersection of author sets - only authors who are in the author sets for all of the postings lists
		# are returned in results - only these authors have all of the query terms as a term in their keywords
		if author_sets:
			matching_authors = set.intersection(*author_sets)
		# Filter out authors who don't have all the keywords
		final_result = {k: v for k, v in author_papers.items() if k in matching_authors}

		return final_result
			 

	def or_search(self, q):
		"""
		Returns authors where at least one of the query terms is found in at least one of the author's papers
		"""

		papers = set()
		# Get list of postings lists, one for each query term
		paper_sets = self.get_paper_sets(q)
		# Get the union of the postings lists
		if paper_sets:
			papers = set.union(*paper_sets)
		authors = []
		author_papers = {}
		#pkw_index = shelve.open(self.pkw_path)
		for paper_id in papers:
			paper_id = paper_id.encode("utf-8")
			if paper_id in self.pkw_index:
				# Add authors of each paper as keys to the results, with paper info as values
				self.add_authors_to_results(author_papers, self.pkw_index, paper_id)


		self.pkw_index.close()

		return author_papers


	def phrase_search(self, q):
		"""
		Return authors where the full query phrase is present in the keywords of at least one of their papers
		"""
		paper_sets = self.get_paper_sets(q)
		papers = set()
		# Get intersection of postings lists - only papers with all the query terms in them are relevant, as
		# we are looking for the full phrase
		if paper_sets:
			papers = set.intersection(*paper_sets)
		
		#pkw_index = shelve.open(self.pkw_path)
		author_papers = {}
		
		for paper_id in papers:
			paper_id = paper_id.encode("utf-8")
			if paper_id in self.pkw_index:
				# For each paper, add the authors to the results if the full phrase is found in the papers keywords
				# Paper keywords are joined into a string to facilitate searching for a phrase
				if q in "|".join(self.pkw_index[paper_id]["keywords"]):
					self.add_authors_to_results(author_papers, self.pkw_index, paper_id)

		self.pkw_index.close()

		return author_papers


	def add_authors_to_results(self, results_dict, pkw_index, paper_id, author_sets=None, index=None):
		"""
		Adds authors to the results dict as keys, and adds paper metadata as values
		"""
		# Get the paper metadata
		title = pkw_index[paper_id]['title']
		authors = pkw_index[paper_id]["authors"]
		url = pkw_index[paper_id]["url"]
		year = pkw_index[paper_id]["year"]
		for author in authors:
			# Author is a name-url pair, make into tuple (rather than list) so can be used as key in dict
			author = tuple(author)
			# If author already key, append new paper info
			if author in results_dict:
				results_dict[author].append((title, url, year))
			# Otherwise add new key and add this paper's info
			else:
				results_dict[author] = [(title, url, year),]
			# For AND searches - each term has a postings list and a corresponding set of authors (the authors of the papers in
			# the postings list). Add this author to the author set for this postings list (i.e. in the same index as the postings list is
			# found in the list of postings lists)
			if(author_sets):
				author_sets[index].add(author)








