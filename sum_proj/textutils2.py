import json
from topia.termextract import extract
import tfidf
import os
from networkx.readwrite import json_graph
import networkx as nx
from nltk import stem

# Paper may or may not have keywords (some Enlighten papers have keywords)
# If they don't, extract keywords and add to data dict
# N.B. using rake but could use something else here (e.g. TFIDF)
# TODO this has nothing to do with the collab graph, do it somewhere else
def add_kw_to_data(ext, data_dict=None):

	if data_dict == None:
		with open("../coauthor_data/School of Computing Science.txt") as f:
			data_dict = json.load(f)

	extractor = extract.TermExtractor()
	extractor.filter = extract.DefaultFilter(singleStrengthMinOccur=4, noLimitStrength=3)
	#extractor.filter = extract.permissiveFilter

	for title, info in data_dict.items():
		# If paper does not already have associated keywords
		if not info["keywords"]:
			text = title + " " + title
			abstract = info["abstract"]
			if abstract:
				if not isinstance(abstract, basestring):
					text += "\n" + abstract[0]
				else:
					text += "\n" + abstract

			# TODO try just titles

			#keyphrases = extractor(text)
			#keyphrases = [kp[0].lower() for kp in keyphrases]
			keyphrases = ext.get_keywords(text, 5)

			data_dict[title]["keywords"] = keyphrases

		# make existing keywords lower case
		else:
			data_dict[title]["keywords"] = [kp.lower() for kp in info["keywords"]]

	return data_dict

def make_stuff():
	ex = tfidf.Tfidf()
	dds_withkw = []
	data_path = ("../coauthor_data/")
	data_files = os.listdir(data_path)
	full_dict = {}
	for data_file in data_files:
		if "full" in data_file:
			continue

		with open(data_path + data_file) as f:
			dd = json.load(f)

		add_the_text(dd, ex)


	for data_file in data_files:
		if "full" in data_file:
			continue

		with open(data_path + data_file) as f:
			dd = json.load(f)

		dd = add_kw_to_data(ex, dd)

		dds_withkw.append(dd)

		with open("../data_with_keywords/" + data_file, 'w') as f:
			json.dump(dd, f)

	return dds_withkw


def add_the_text(dd, ext):
	for title, info in dd.items():
		# If paper does not already have associated keywords
		text = title
		abstract = info["abstract"]
		if abstract:
			if not isinstance(abstract, basestring):
				text += "\n" + abstract[0]
			else:
				text += "\n" + abstract

		ext.add_text(text)

def make_author_kw():
	extractor = extract.TermExtractor()
	extractor.filter = extract.DefaultFilter(singleStrengthMinOccur=4, noLimitStrength=3)
	tf2 = tfidf.Tfidf()

	akws = []
	data_path = ("../data_with_keywords/")
	data_files = os.listdir(data_path)
	for data_file in data_files:
		
		with open(data_path + data_file) as f:
			dd = json.load(f)

		for info in dd.values():
			authors = info["authors"]
			keywords = info["keywords"]
			kw_string = " ".join(keywords)
			tf2.add_text(kw_string)

	for data_file in data_files:
		print data_file
		authorkw = {}
		with open(data_path+data_file) as f:
			dd = json.load(f)

		for info in dd.values():
			authors = info["authors"]
			keywords = info["keywords"]

			for author in authors:
				name = author[0]
				aid = author[1]

				if aid not in authorkw:
					authorkw[aid] = {"name":name, "keywords": keywords}
				else:
					authorkw[aid]["keywords"].extend(keywords)

		
		for author, info in authorkw.items():
			kw_string = " ".join(info["keywords"])
			new_kw = tf2.get_keywords(kw_string, 20)
			authorkw[author]["keywords"] = new_kw

		with open("../author_kw/"+data_file, 'w') as f:
			json.dump(authorkw, f)

		#print "appending " + data_file + " akw to akws"
		akws.append(authorkw)


	# for akw in akws:
	# 	for author, info in akw.items():
	# 		kw_string = " ".join(info["keywords"])
	# 		new_kw = tf2.get_keywords(kw_string, 20)
	# 		akw[author]["keywords"] = new_kw

	# 	with open("../author_kw/"+data_file, 'w') as f:
	# 		json.dump(akw, f)


	return akws



def make_sim_graph(akw, name):

	with open("../grc/graphs/collab/" + name) as f:
		gdata = json.load(f)

	col_graph = json_graph.node_link_graph(gdata)

	sim_graph = nx.Graph()

	authors = akw.keys()
	values = akw.values()

	for i in range (0, len(authors)):
		author1 = authors[i]
		author1name = values[i]["name"]
		sim_graph.add_node(author1, {
									"name": author1name, 
									"in_school":col_graph.node[author1]["in_school"],
									"paper_count":col_graph.node[author1]["paper_count"]
									})

		keywords = values[i]["keywords"]
		stemmed1 = stem_words(keywords[:])

		for j in range(i+1, len(authors)):
			author2 = authors[j]
			author2name = values[j]["name"]
			sim_graph.add_node(author2, {
										"name":author2name,
										"in_school":col_graph.node[author1]["in_school"],
										"paper_count":col_graph.node[author1]["paper_count"]
										})

			keywords2 = values[j]["keywords"]
			stemmed2 = stem_words(keywords2[:])

			sim = check_sim(stemmed1, stemmed2)
			ratio = sim[0]
			indices = sim[1]
			matched_words = []
			if len(keywords) > len(keywords2):
				longest = keywords
			else:
				longest = keywords2


			for index in indices:
				matched_words.append(longest[index])

			if ratio > 0.2:
				sim_graph.add_edge(author1, author2, {"num_collabs":ratio, "sim_kw": matched_words})

	return sim_graph



def check_sim(kw1, kw2):
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

	ratio = (count*1.0) / len(longest)
	return (ratio, match_indices)




def stem_words(words):
# WAIT should the keywords in author keywords be stemmed???
# Yes - gives better chance of finding a match... More recall, less precision
	# TODO initialise these somewhere else
	prtr = stem.porter.PorterStemmer()
	#wnl = WordNetLemmatizer()
	# So as not to change original list... to be discussed
	words_copy = words[:]
	for index, word in enumerate(words_copy):
		# Use a better split here
		tokens = word.split()
		#stemmed_phrase = ""
		stemmed_token = ""
		for token in tokens:
			stemmed_token = prtr.stem(token).lower()
			#stemmed_phrase += stemmed_token + " "

		if stemmed_token:
			words[index] = stemmed_token.strip()

	return words


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









