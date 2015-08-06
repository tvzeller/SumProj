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
#from difflib import SequenceMatcher 
import Levenshtein
from fuzzywuzzy import fuzz
from collections import defaultdict
import enlighten_scraper as es
import graph_from_dict as gfd
import time
import commontest



#######################################################################
## TODO TODO moved add_kw function to here from gfd, needs adapting ###


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
		#stemmed_kw_list = keyword_list[:]
		# TODO temporary fixes
		stemmed_kw_list = [kw for kw in stemmed_kw_list if "abstract avail" not in kw]
		# TODO do we need to check if authors exists?
		for author in authors:
			# TODO Add a node to collab graph here
			gm.add_vertex(author)
			# Make list of keywords into a single string, with phrases separated by a divisor
			# TODO using kw list for now
			#kw_string = "|".join(stemmed_kw_list)
			author_name = author[0]
			# TODO have to do this to work with shelve because loading from json for now
			author_id = author[1].encode("utf-8")
			# Add author to authorkw_dict / add keywords to existing author
			# TODO using kw list but may become string
			if author_id not in authorkw_dict:
				authorkw_dict[author_id] = {"name": author_name, "keywords": stemmed_kw_list}
			else:
				authorkw_dict[author_id]["keywords"].extend(stemmed_kw_list)
			# NB each author is a (name, unique id) pair; unique id is dict key, name goes as value

		# Add edges to collab graph here
		gm.add_links(title, authors)
		# Potentially add to inv_index here as we are already looping through the data_dict
	
	clean_authorkw = clean_keywords(authorkw_dict.copy())
	# store collab graph (as json?)
	gm.write_to_file("newcsgraph")
	# store authorkw_dict (using shelve for now)
	she = shelve.open("authorkw.db")
	she.update(authorkw_dict)
	she.close()
	# TODO
	return (clean_authorkw, gm.get_graph())



# Paper may or may not have keywords (some Enlighten papers have keywords)
# If they don't, extract keywords and add to data dict
# N.B. using rake but could use something else here (e.g. TFIDF)
# TODO this has nothing to do with the collab graph, do it somewhere else
def add_kw_to_data(self):
	ex = tfidf.Extractor()
	
	for title in self.data_dict:
	 	text = self.get_text(title)
	 	ex.add_text(text)

	rk = rake.Rake()
	rk.add_stopwords("stopwords.txt")

	for title, info in self.data_dict.items():
		# If paper does not already have associated keywords
		if not info["keywords"]:
			text = self.get_text(title)
			# rk returns keywords as a list
			# join on "|" and set as keywords for this paper
			# TODO nb we have keywords as string to allow for phrase search (search for substring in keyword string)
			keyphrases = rk.get_keyphrases(text)
			print keyphrases
			# tfidf_words = ex.get_keywords(text)
			# for i, kp in enumerate(keyphrases):
			# 	tokens = kp.split()
			# 	filtered_phrase = ""
			# 	for token in tokens:
			# 		if token in tfidf_words:
			# 			filtered_phrase += token + " "
			# 	keyphrases[i] = filtered_phrase
			#print keyphrases
			#time.sleep(2)

			self.data_dict[title]["keywords"] = keyphrases
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

def clean_keywords(kwdict):
	for author in kwdict:
		kw = kwdict[author]["keywords"]
		kwdict[author]["keywords"] = commontest.remove_bad2(kw)
	return kwdict

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
		kw_tokens1 = akw_dict[author1]["keywords"] #.split("|")
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
			kw_tokens2 = akw_dict[author2]["keywords"] #.split("|")
			sim_check = similar(kw_tokens1, kw_tokens2)
			sim_match = sim_check[0]
			sim_kw = sim_check[1]
			#sim_match = Levenshtein.setratio(kw_tokens1, kw_tokens2)
			# TODO try different thresholds, 0.6 is high
			#print sim_match
			#print author1_name
			#print author2_name
			#time.sleep(0.5)
			if sim_match >= 0.2:
				#print "matching authors"
				#print author2_name
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
			#ratio = SequenceMatcher(None, kw1, kw2).quick_ratio()
			#ratio = Levenshtein.ratio(kw1, kw2)
			# Threshold increases the smaller the keyword
			#threshold = min(1.0, (1.0 / min(len(kw1.split()), len(kw2.split())) + 0.2))
			# we need half of the longest string to have matches for dice to be above this threshold
			threshold = (1.0 * max(len(kw1.split()), len(kw2.split()))) / len(kw1.split() + kw2.split())
			#ratio = fuzz.partial_ratio(kw1, kw2)
			ratio = dice(kw1, kw2)
			# TODO try different thresholds
			# if ratio is above threshold, add both indices to respective index set
			# Python: "As a rule of thumb, a ratio() value over 0.6 means the sequences are close matches" (for difflib ratio)
			if ratio >= threshold:
				indices1.add(kw1_index)
				indices2.add(kw2_index)
				sim_keywords.append(kw1)
				sim_keywords.append(kw2)
				print kw1
				print kw2
				time.sleep(1)
				break

	for kw2_index, kw2 in enumerate(kw_list2):
		for kw1_index, kw1 in enumerate(kw_list1):
			if kw2_index not in indices2 and kw1_index in indices1:
				#ratio = SequenceMatcher(None, kw1, kw2).quick_ratio()
				#ratio = Levenshtein.ratio(kw1, kw2)
				#threshold = 1.0 / min(len(kw1.split()), len(kw2.split()))
				threshold = (1.0 * max(len(kw1.split()), len(kw2.split()))) / len(kw1.split() + kw2.split())
				#ratio = fuzz.partial_ratio(kw1, kw2)
				ratio = bi_dice(kw1, kw2)
				if ratio >= threshold:
					indices2.add(kw2_index)
					indices1.add(kw1_index)
					sim_keywords.append(kw1)
					sim_keywords.append(kw2)
					break

	pct_match1 = (len(indices1) * 1.0) / len(kw_list1)
	pct_match2 = (len(indices2) * 1.0) / len(kw_list2)
	match = (pct_match1 + pct_match2) / 2
	#print "final score is: " + str(match)
	return (match, sim_keywords)

# can do on word level or bigram level - see http://www.catalysoft.com/articles/StrikeAMatch.html
def dice(str1, str2):
	tokens1 = set(str1.split())
	tokens2 = set(str2.split())
	inter = tokens1.intersection(tokens2)

	return (2.0 * len(inter)) / (len(tokens1) + len(tokens2))

def bi_dice(str1, str2):
	
	pairs1 = word_letter_pairs(str1)
	pairs2 = word_letter_pairs(str2)
	
	if pairs1 or pairs2:
		union = len(pairs1) + len(pairs2)
		inter = set(pairs1).intersection(set(pairs2))
		return (2.0 * len(inter)) / union
	
	else:
		return 0.0


def word_letter_pairs(phrase):
	all_pairs = []
	tokens = phrase.split()
	for token in tokens:
		all_pairs.extend(letter_pairs(token))
	return all_pairs

def letter_pairs(word):
	pairs = []
	for i in range(0, len(word)-1):
		pairs.append(word[i:i+2])
	return pairs
			









