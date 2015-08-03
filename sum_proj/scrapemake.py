# This script will get raw data and reorganise it in some data structures:
# 1. Use es to scrape enlighten to get the data for all of the below
# 2. Use gfd to make graph, then store it
# 3. Make an {author: keywords} dict (using keyword extraction module), then store it
# 4. Call some other module to make a keyword similarity graph, then store it
# 5. Use search.py or wherever that code goes to make an inverted index ({term: authors}), then store it

import shelve
import networkx as nx
from nltk import stem
# prtr = stem.porter.PorterStemmer()
# prtr.stem("word") (i think it only works on individual terms)
from nltk.stem.wordnet import WordNetLemmatizer
# wnl = WordNetLemmatizer()
# wnl.lemmatize("word")
from difflib import SequenceMatcher 
import Levenshtein
from collections import defaultdict
import enlighten_scraper as es
import graph_from_dict as gfd
import time


# get data_dict
# add keywords to data
# stem and lem keywords - should there be some sort of word processing module, maybe not necessary
# TODO NB passing data as a parameter, in future, this will do the scraping
def scrape_and_make(data_dict):
	#authorkw_dict = defaultdict(str)
	authorkw_dict = {}
	names = es.get_names("http://www.gla.ac.uk/schools/computing/staff/")
	# TODO do we need to pass dd into gm?
	gm = gfd.GraphMaker(data_dict, names)
	# TODO adding of keywords has to be done somewhere else - text processing module...
	#gm.add_kw_to_data()

	for title, info in data_dict.items():
		authors = info["authors"]
		# At this point kws are in a list of phrases (returned that way from es and from kw extraction)
		# First, stem or lemmatize each word in each phrase (or don't)
		# To add to author kw, join on "|" so we have a full string which can be searched for substring
		# Then we need to tokenise that into individual terms to put in inv index
		# Use regex to split into terms.. take into account "|"
		# Once tokenised, build inv index like in search.py
		keyword_list = info["keywords"]
		# TODO temporary fixes
		keyword_list = [kw for kw in keyword_list if kw != ""]
		stemmed_kw_list = stem_kwlist(keyword_list)
		# TODO temporary fixes
		stemmed_kw_list = [kw for kw in keyword_list if "abstract avail" not in kw]
		# TODO do we need to check if authors exists?
		for author in authors:
			# TODO Add a node to collab graph here
			gm.add_vertex(author)
			# Make list of keywords into a single string, with phrases separated by a divisor
			kw_string = "|".join(stemmed_kw_list)
			author_name = author[0]
			# TODO have to do this to work with shelve because loading from json for now
			author_id = author[1].encode("utf-8")
			# Add author to authorkw_dict / add keywords to existing author
			if author_id not in authorkw_dict:
				authorkw_dict[author_id] = {"name": author_name, "keywords": kw_string}
			else:
				authorkw_dict[author_id]["keywords"] += kw_string + "|"
			# NB each author is a (name, unique id) pair; unique id is dict key, name goes as value

		# Add edges to collab graph here
		gm.add_links(title, authors)
		# Potentially add to inv_index here as we are already looping through the data_dict

	# store collab graph (as json?)
	gm.write_to_file("newcsgraph")
	# store authorkw_dict (using shelve for now)
	she = shelve.open("authorkw.db")
	she.update(authorkw_dict)
	she.close()
	# TODO
	return (authorkw_dict, gm.get_graph())


# make inv index based on data_dict / author_kw dict (or do this while looping above)

# Either do one or the other, or neither
def stem_kwlist(kw_list):
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

def make_sim_graph(my_tup):
# Make similarity graph:
# for each author in authorkw_dict:
# tokenise keywords, stem etc.
# add node to sim graph
# check similarity between this node and node + i keywords
# if sim > threshold, add edge between nodes
	# TODO TODO
	akw_dict = my_tup[0]
	collab_graph = my_tup[1]
	authors = [author for author in collab_graph.node if collab_graph.node[author]["in_school"]]
	# TODO AKW DICT should only contain school authors
	full_start = time.time()

	sim_graph = nx.Graph()
	#authors = akw_dict.keys()
	for i in range(0, len(authors)):
		start = time.time()
		author1 = authors[i]
		# split kw string into phrase tokens
		kw_tokens1 = akw_dict[author1]["keywords"].split("|")
		author1_name = akw_dict[author1]["name"]
		author1_id = author1
		sim_graph.add_node(author1_id, {"name": author1_name})
		print "checking:", author1_name
		print "author %d of %d" % (i, len(authors))
		for j in range(i+1, len(authors)):
			author2 = authors[j]
			author2_name = akw_dict[author2]["name"]
			author2_id = author2
			sim_graph.add_node(author2_id, {"name": author2_name})
			kw_tokens2 = akw_dict[author2]["keywords"].split("|")
			sim_check = similar(kw_tokens1, kw_tokens2)
			sim_match = sim_check[0]
			sim_kw = sim_check[1]
			if sim_match >= 0.2:
				# add edge between authors
				# TODO have keywords as edge attribute?
				sim_graph.add_edge(author1, author2, {"sim_keywords": sim_kw})
		print "time taken:", time.time() - start

	print "total time taken:", time.time() - full_start
	return sim_graph
				

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
	sim_keywords = []
	for kw1_index, kw1 in enumerate(kw_list1):
		for kw2_index, kw2 in enumerate(kw_list2):
			# This uses the SequenceMatcher class from difflib to get string similarity metric 
			# TODO explore using different algorithms instead
			# TODO try Levenshtein
			#ratio = SequenceMatcher(None, kw1, kw2).quick_ratio()
			ratio = Levenshtein.ratio(kw1, kw2)
			#ratio = 0.2
			#print kw1, kw2, ratio
			# TODO try different thresholds
			# if ratio is above threshold, add both indices to respective index set
			# Python: "As a rule of thumb, a ratio() value over 0.6 means the sequences are close matches" (for difflib ratio)
			if ratio >= 0.7:
				indices1.add(kw1_index)
				indices2.add(kw2_index)
				# if match found, break out of inner loop
				sim_keywords.append(kw1)
				sim_keywords.append(kw2)
				break

	for kw2_index, kw2 in enumerate(kw_list2):
		for kw1_index, kw1 in enumerate(kw_list1):
			if kw2_index not in indices2 and kw1_index in indices1:
				#ratio = SequenceMatcher(None, kw1, kw2).quick_ratio()
				ratio = Levenshtein.ratio(kw1, kw2)
				if ratio >= 0.7:
					indices2.add(kw2_index)
					indices1.add(kw1_index)
					sim_keywords.append(kw1)
					sim_keywords.append(kw2)
					break

	pct_match1 = (len(indices1) * 1.0) / len(kw_list1)
	pct_match2 = (len(indices2) * 1.0) / len(kw_list2)
	match = (pct_match1 + pct_match2) / 2
	#print "final score is: " + str(match)
	# TODO try different thresholds
	if match >= 0.2:
		print "matching authors"
	return (match, sim_keywords)
			









