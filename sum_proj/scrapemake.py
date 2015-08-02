# This script will get raw data and reorganise it in some data structures:
# 1. Use es to scrape enlighten to get the data for all of the below
# 2. Use gfd to make graph, then store it
# 3. Make an {author: keywords} dict (using keyword extraction module), then store it
# 4. Call some other module to make a keyword similarity graph, then store it
# 5. Use search.py or wherever that code goes to make an inverted index ({term: authors}), then store it

import networkx as nx
from nltk import stem
# prtr = stem.porter.PorterStemmer()
# prtr.stem("word") (i think it only works on individual terms)
from nltk.stem.wordnet import WordNetLemmatizer
# wnl = WordNetLemmatizer()
# wnl.lemmatize("word")
from difflib import SequenceMatcher 
from collections import defaultdict


# get data_dict
# add keywords to data
# stem and lem keywords - should there be some sort of word processing module, maybe not necessary

authorkw_dict = defaultdict(str)
for title, info in data_dict.items():
	authors = info["authors"]
	# At this point kws are in a list of phrases (returned that way from es and from kw extraction)
	# First, stem or lemmatize each word in each phrase (or don't)
	# To add to author kw, join on "|" so we have a full string which can be searched for substring
	# Then we need to tokenise that into individual terms to put in inv index
	# Use regex to split into terms.. take into account "|"
	# Once tokenised, build inv index like in search.py
	keyword_list = info["keywords"]
	stemmed_kw_list = stem_and_lem(keyword_list)
	# TODO do we need to check if authors exists?
	for author in authors:
		# TODO Add a node to collab graph here
		# Make list of keywords into a single string, with phrases separated by a divisor
		kw_string = "|".join(stemmed_kw_list)
		# Add author to authorkw_dict / add keywords to existing author
		# NB each author is a (name, unique id) pair; keep this tuple as the dict key for now TODO TODO
		# TODO experiment with this
		authorkw_dict[author] += keywords +"|"

	# Add edges to collab graph here
	# Potentially add to inv_index here as we are already looping through the data_dict

# store collab graph (as json?)
# store authorkw_dict (using shelve for now)


# make inv index based on data_dict / author_kw dict (or do this while looping above)

# Either do one or the other, or neither
def stem_or_lem(kw_list):
# WAIT should the keywords in author keywords be stemmed???
# Yes - gives better chance of finding a match... More recall, less precision
	# TODO initialise these somewhere else
	prtr = stem.porter.PorterStemmer()
	wnl = WordNetLemmatizer()
	# So as not to change original list... to be discussed
	kw_copy = kw_list[:]
	for index, keyphrase in enumerate(kw_copy):
		# Use a better split here
		key_tokens = keyphrase.split()
		stemmed_phrase = ""
		for token in key_tokens:
			stemmed_token = prtr.stem(token)
			stemmed_phrase += stemmed_token + " "

		kw_copy[index] = stemmed_phrase.strip()

	return kw_copy

def make_sim_graph(akw_dict):
# Make similarity graph:
# for each author in authorkw_dict:
# tokenise keywords, stem etc.
# add node to sim graph
# check similarity between this node and node + i keywords
# if sim > threshold, add edge between nodes
	sim_graph = nx.Graph()
	authors = akw_dict.keys()
	for i in range(0, len(authors)):
		author1 = authors[i]
		# split kw string into phrase tokens
		kw_tokens1 = akw_dict[author1].split("|")
		author1_name = author1(0)
		author1_id = author1(1)
		sim_graph.add_node(author1_id, {"name": author1_name})
		for j in range(i+1, len(authors)):
			author2 = authors[j]
			author2_name = author2(0)
			author2_id = author2(1)
			sim_graph.add_node(author2_id, {"name": author2_name})
			kw_tokens2 = akw_dict[author2].split("|")
			is_sim = similar(kw_tokens1, kw_tokens2)
			if is_sim:
				# add edge between authors
				# TODO have keywords as edge attribute?
				sim_graph.add_edge(author1, author2)
				

# to determine similarity between 2 lists of keywords
# for each kw in l1, compare against all kw in l2 using string similarity measure (from difflib, nltk or something)
# if keyword pair matches above a certain threshold, consider it a match
# if match, add kw1 index to set1, add kw2 index to set2
# final sets will contain the indices of all kw in each set which have a match in the other set
# get percentage of each kw list which have match (len set / len list)
# get average of those percentages - final result; if above certain threshold, authors have similar keywords
# Difficulties - each author does not have a set of neat, uniform distinct keywords, they may have several similar keywords/phrases as extraction
# is not perfect. 
def similar(kw_list1, kw_list2):
	tot_sim = 0.0
	indices1 = set()
	indices2 = set()
	for i, kw1 in enumerate(kw_list1):
		for j, kw2 in enumerate(kw_list2):
			# This uses the SequenceMatcher class from difflib to get string similarity metric 
			# TODO explore using different algorithms instead
			ratio = SequenceMatcher(None, kw1, kw2).ratio()
			#print kw1, kw2, ratio
			# TODO try different thresholds
			# if ratio is above threshold, add both indices to respective index set
			if ratio > 0.65:
				indices1.add(i)
				indices2.add(j)

	pct_match1 = (len(indices1) * 1.0) / len(kw_list1)
	pct_match2 = (len(indices2) * 1.0) / len(kw_list2)
	match = (pct_match1 + pct_match2) / 2
	#print "final score is: " + str(match)
	# TODO try different thresholds
	return match >= 0.5
			









