import json
from topia.termextract import extract
import tfidf
import os
from networkx.readwrite import json_graph
import networkx as nx
from nltk import stem
import operator


def get_data_with_keywords(data_dicts):
	"""
	Takes a list of paper metadata dicts and adds keywords to each one
	"""
	# New Tfidf object
	tfidf_ext = tfidf.Tfidf()
	dds_withkw = []

	# For each data_dict, add text of papers to tfidf corpus
	for dd in data_dicts:
		add_the_text(dd, ex)

	# For each data_dict, add keywords to the data
	for dd in data_dicts:
		dd = add_kw_to_data(dd, tfidf_ext)

		dds_withkw.append(dd)

	return dds_withkw


def add_the_text(dd, ext):
	"""
	Adds the text of each paper in the given data dict to the corpus of the given Tfidf object
	"""
	for paper_id, info in dd.items():
		text = get_paper_text(info)
		ext.add_text(text)


def get_paper_text(paper_info):
	"""
	Takes a value from data dict (a paper's metadata) and gets the text for a paper by
	concatenating title and abstract 
	"""
	title = info['title']
	# If paper does not already have associated keywords
	if not info["keywords"]:
		text = title
		abstract = info["abstract"]
		if abstract:
			if not isinstance(abstract, basestring):
				text += "\n" + abstract[0]
			else:
				text += "\n" + abstract
	return text


def add_kw_to_data(data_dict, extrctr=None, max_keywords=5):
	"""
	Given a data_dict, adds keywords to the metadata of each paper
	May take an existing Tfidf object and maximum amount of keywords to add.
	If no Tfidf object passed, uses Topia TermExtractor to extract keywords
	"""

	if(extrctr==None):
		extrctr = extract.TermExtractor()
		extrctr.filter = extract.permissiveFilter
		topia_extraction = True

	for paper_id, info in data_dict.items():
		# Paper may already have keywords from Enlighten
		if not info["keywords"]:
			text = get_paper_text(info)
			# Title is already included in text, but add it again so the words in the title get extra weight
			# (they are more likely to be keywords in most cases)
			text = text + " " + info['title']

			if topia_extraction:
				keywords = extrctr(text)
				# topia term extraction returns list of keywords/phrases + score tuples - we only want the actual words
				keywords = [kw[0].lower() for kw in keywords]
			else:
				# With tfidf we can specify the maximum amount of keywords we want returned
				keywords = extrctr.get_keywords(text, max_keywords)

			data_dict[paper_id]["keywords"] = keywords

		# make existing keywords (that came from scraping) lower case
		else:
			data_dict[paper_id]["keywords"] = [kw.lower() for kw in info["keywords"]]

	return data_dict


def make_index(data_dict):
	"""
	Takes a data_dict and makes an inverted index, with terms as keys 
	and the ids of papers containing the terms as values.
	"""
	
	inv_index = defaultdict(set)
	for paper_id in data_dict:
		# Join keyword list and pass to process text
		terms = set(self.process_text(" ".join(data_dict[paper_id]["keywords"])))
		# For each keyword term in this paper, add paper_id to postings set
		for term in terms:
			# Has to be utf encoded to work with shelve module
			term = term.encode("utf-8")
			inv_index[term].add(paper_id)

	return inv_index

# Processes the keywords to put in index - makes them lowercase and stems
# Also used on search queries, to ensure consistency
def process_text(text):
	prtr = stem.porter.PorterStemmer()
	# Tokenise
	tokens = text.lower().split()
	# Stem tokens and put back in list
	tokens = [prtr.stem(token) for token in tokens]

	return tokens


def make_paper_kw_index(data_dict):
	pkw = {}
	for paper_id, info in data_dict.items():
		paper_id = paper_id.encode("utf-8")
		del info["abstract"]
		pkw[paper_id] = info

	return pkw


def make_author_kw_dicts(data_dicts):
	"""
	Takes list of data_dicts and makes, for each one, an dict mapping author ids to a dict containing their
	name and their keywords. Returns list of all the author-keyword dicts
	"""

	tfidf_ext = tfidf.Tfidf()
	akws = []

	for dd in data_dicts:
		# For each paper, add it's keywords to a Tfidf object corpus	
		for info in dd.values():
			keywords = info["keywords"]
			kw_string = " ".join(keywords)
			tfidf_ext.add_text(kw_string)

	for dd in data_dicts:
		authorkw = {}

		for info in dd.values():
			authors = info["authors"]
			keywords = info["keywords"]

			for author in authors:
				# Add author as key and add name and keywords of the paper as values
				name = author[0]
				author_id = author[1]

				if author_id not in authorkw:
					authorkw[author_id] = {"name":name, "keywords": keywords}
				else:
					authorkw[author_id]["keywords"].extend(keywords)

		# For each author in the new authorkw dict, calculate the tfidf scores of each of their
		# keywords and take the highest scoring one as the final author keywords
		for author, info in authorkw.items():
			keywords = info["keywords"]
			kw_string = " ".join(keywords)

			new_kw = tfidf_ext.get_keywords(kw_string, 20)
			authorkw[author]["keywords"] = new_kw

		akws.append(authorkw)

	return akws



def get_most_frequent(wordlist, maxwords):
	"""
	Takes a list of words and a number maxwords and returns a list of the most frequent words,
	up to maxwords
	"""

	wordcounts = {}
	for word in wordlist:
		if word not in wordcounts:
			wordcounts[word] = wordlist.count(word)

	topwords = sorted(wordcounts.items(), key=operator.itemgetter(1), reverse=True)
	topwords = [wordscore[0] for wordscore in topwords]
	return topwords[:maxwords]


def check_kw_sim(kw1, kw2):
	"""
	Gets the similarity ratio of two lists of keywords
	"""
	# Get longest of the two lists
	if len(kw1) > len(kw2):
		longest = kw1
		shortest = kw2
	else:
		longest = kw2
		shortest = kw1

	# Count to keep track of matching words
	count = 0
	# List of the indices of matching word in the keyword list 
	match_indices = []
	for index, word1 in enumerate(longest):
		for word2 in shortest:
			if word1 == word2:
				count += 1
				match_indices.append(index)
				break

	# Return the percentage of words with a match and the indices where they are found
	ratio = (count*1.0) / len(longest)
	return (ratio, match_indices)


def stem_word_list(word_list):
	"""
	Takes a list of words and returns a list containing the stemmed versions of the words
	"""
	prtr = stem.porter.PorterStemmer()
	words_copy = word_list[:]
	for index, word in enumerate(words_copy):
		tokens = word.split()
		stemmed_token = ""
		for token in tokens:
			stemmed_token = prtr.stem(token).lower()

		if stemmed_token:
			word_list[index] = stemmed_token.strip()

	return word_list









