import json
from topia.termextract import extract
import tfidf
import os
from networkx.readwrite import json_graph
import networkx as nx
from nltk import stem


def get_data_with_keywords(data_dicts):
	tfidf_ext = tfidf.Tfidf()
	dds_withkw = []

	full_dict = {}
	for dd in data_dicts:
		add_the_text(dd, ex)

	for dd in data_dicts:
		dd = add_kw_to_data(dd, tfidf_ext)

		dds_withkw.append(dd)

		#with open("../data_with_keywords/" + data_file, 'w') as f:
		#	json.dump(dd, f)

	return dds_withkw


def add_the_text(dd, ext):
	for paper_id, info in dd.items():
		text = get_paper_text(info)
		ext.add_text(text)


def get_paper_text(paper_info):
	title = info['title']
	# If paper does not already have associated keywords
	if not info["keywords"]:
		text = title + " " + title
		abstract = info["abstract"]
		if abstract:
			if not isinstance(abstract, basestring):
				text += "\n" + abstract[0]
			else:
				text += "\n" + abstract
	return text



# Paper may or may not have keywords (some Enlighten papers have keywords)
# If they don't, extract keywords and add to data dict
def add_kw_to_data(data_dict, extrctr=None, max_keywords=5):
	if(extrctr==None):
		extrctr = extract.TermExtractor()
		extrctr.filter = extract.permissiveFilter
		topia_extraction = True

	
	for paper_id, info in data_dict.items():
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



# TODO can record size of postings to optimise intersections - faster if start intersecting with smallest set; 
# see Intro to IR pg.11
# TODO also record amount of times author has this term 
# TODO note takes data_dict with keywords
def make_index(data_dict):
	inv_index = defaultdict(set)
	for paper_id in data_dict:
		# Join keyword list and pass to process text
		terms = set(self.process_text(" ".join(data_dict[paper_id]["keywords"])))
		#terms = set(self.process_text(text))
		# Authors is list of lists, we want second element in list (the unique identifier)
		authors = [author[1] for author in data_dict[paper_id]["authors"]]
		#authors = [(author[0], author[1]) for author in data_dict[title]["authors"]]
		# For each keyword term in this paper, add authors to postings set
		if "java" in terms:
			print data_dict[paper_id]["title"]
		for term in terms:
			# Has to be encoded to work with shelve module
			term = term.encode("utf-8")
			inv_index[term].add(paper_id)

	return inv_index

# Processes the keywords to put in index - makes them lowercase and stems
# Also used on search queries, to ensure consistency
def process_text(text):
	prtr = stem.porter.PorterStemmer()
	# Tokenise
	tokens = text.lower().split()
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
	tfidf_ext = tfidf.Tfidf()

	akws = []
	for dd in data_dicts:
		
		for info in dd.values():
			authors = info["authors"]
			keywords = info["keywords"]
			#TODOTODOTODO now tfidf just returning keywords
			kw_string = " ".join(keywords)
			tfidf_ext.add_text(kw_string)

	for dd in data_dicts:
		authorkw = {}

		for info in dd.values():
			authors = info["authors"]
			keywords = info["keywords"]

			for author in authors:
				name = author[0]
				author_id = author[1]

				if author_id not in authorkw:
					authorkw[author_id] = {"name":name, "keywords": keywords}
				else:
					authorkw[author_id]["keywords"].extend(keywords)

		
		for author, info in authorkw.items():
			keywords = info["keywords"]
			kw_string = " ".join(keywords)

			new_kw = tfidf_ext.get_keywords(kw_string, 20)
			authorkw[author]["keywords"] = new_kw

		#with open("../author_kw/"+data_file, 'w') as f:
		#	json.dump(authorkw, f)

		akws.append(authorkw)

	return akws



def get_most_frequent(wordlist, maxwords):
	wordcounts = {}
	for word in wordlist:
		if word not in wordcounts:
			wordcounts[word] = wordlist.count(word)

	topwords = sorted(wordcounts.items(), key=operator.itemgetter(1), reverse=True)
	topwords = [wordscore[0] for wordscore in topwords]
	return topwords[:maxwords]


def check_kw_sim(kw1, kw2):
	if len(kw1) > len(kw2):
		longest = kw1
		shortest = kw2
	else:
		longest = kw2
		shortest = kw1

	count = 0
	match_indices = []
	for index, word1 in enumerate(longest):
		for word2 in shortest:
			if word1 == word2:
				count += 1
				match_indices.append(index)
				break

	ratio = (count*1.0) / len(longest)
	return (ratio, match_indices)


def stem_word_list(word_list):
	# TODO initialise these somewhere else
	prtr = stem.porter.PorterStemmer()
	# So as not to change original list... to be discussed
	words_copy = word_list[:]
	for index, word in enumerate(words_copy):
		tokens = word.split()
		stemmed_token = ""
		for token in tokens:
			stemmed_token = prtr.stem(token).lower()

		if stemmed_token:
			word_list[index] = stemmed_token.strip()

	return word_list


def make_all_sims():
	simgraphs = []
	data_path = ("../author_kw/")
	data_files = os.listdir(data_path)
	for data_file in data_files:
		name = data_file.split(".")[0] + ".json"
		with open(data_path+data_file) as f:
			akw = json.load(f)

		g = make_sim_graph(akw, name)
		simgraphs.append(g)

		gdata = json_graph.node_link_data(g)
		name = data_file.split(".")[0] + ".json"
		with open("../simgraphs/" + name, 'w') as f:
			json.dump(gdata, f)

	return simgraphs









