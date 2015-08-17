import graph_from_dict as gfd
import enlighten_scraper as es
import json
from lxml import html
import os
import networkx as nx
from networkx.readwrite import json_graph
import search
import shelve
import textutils2

def graph_me_up():
	with open("../coauthor_data/School of Computing Science.txt") as f:
		d = json.load(f)

	names = es.get_names("http://www.gla.ac.uk/schools/computing/staff/")

	gm = gfd.GraphMaker(d, names)

	g = gm.get_graph()

	gm.write_to_file("cslatest")

	return g

def get_and_graph():
	schools_tree = es.get_tree("http://www.gla.ac.uk/schools/")
	ns = 'http://exslt.org/regular-expressions'
	path = '//div[@class="row standardContent"]//a[re:match(@href, "schools/[A-Za-z]+/")]'
	a_elems = schools_tree.xpath(path, namespaces={'re':ns})
	base_url = "http://www.gla.ac.uk"
	urls = []
	names = []

	for a in a_elems:
		staff_page_url = base_url + a.get("href") + "staff/"
		urls.append(staff_page_url)
		school_name = a.text
		names.append(school_name)

	school_names_urls = zip(names, urls)
	print school_names_urls

	#remove SOCS as done already, physics for now cause it's huge
	for tup in school_names_urls[:]:
		if "Physics" in tup[0]:
			school_names_urls.remove(tup)


	# For each school
	for name, url in school_names_urls:
		print name, url

		if "Humanities" in name:
			name = "School of Humanities"
		author_name_urls = es.get_author_name_urls(name, url)
		# write these to file for safe keeping
		# ALREADY BEING DONE BY ES
		#with open("../nameurls/" + name + ".txt", 'w') as f:
		#	json.dump(author_name_urls)
		coauthor_dict = es.get_coauthors_dict(author_name_urls, name)
		# extract just names from name urls and put in list
		#author_names = [author_name for author_name, author_url in author_name_urls]

		# Put names in Title First Name Last Name order
		for title, data in coauthor_dict.items():
			authors = data["authors"]
			newauthors = [(anu[0].split(", ")[1] + " " + anu[0].split(", ")[0], anu[1]) for anu in authors]
			coauthor_dict[title]["authors"] = newauthors

		# Do the same for author_name_urls
		# TODO is this necessary? Because we're checking against urls - could even just give gm the urls
		author_name_urls = [(anu[0].split(", ")[1] + " " + anu[0].split(", ")[0], anu[1]) for anu in author_name_urls]
		# now make graph
		gm = gfd.GraphMaker()
		gm.populate_graph(coauthor_dict, author_name_urls)
		gm.add_metrics()
		gm.write_to_file("../newestgraphs/" + name + ".json")

def graphs_from_files():
	filenames = ["Adam Smith Business School",
				"Dental School",
				"School of Chemistry",
				"School of Critical Studies",
				"School of Culture and Creative Arts",
				"School of Education"
				]

	schools_tree = es.get_tree("http://www.gla.ac.uk/schools/")
	ns = 'http://exslt.org/regular-expressions'
	path = '//div[@class="row standardContent"]//a[re:match(@href, "schools/[A-Za-z]+/")]'
	a_elems = schools_tree.xpath(path, namespaces={'re':ns})
	base_url = "http://www.gla.ac.uk"
	urls = []
	names = []

	for a in a_elems:
		staff_page_url = base_url + a.get("href") + "staff/"
		urls.append(staff_page_url)
		school_name = a.text
		names.append(school_name)

	school_names_urls = zip(names, urls)
	print school_names_urls


	for name, url in school_names_urls:
		if name in filenames:
			with open("../coauthor_data/" + name + ".txt") as f:
				d = json.load(f)

			staff_names = es.get_names(url)
			gm = gfd.GraphMaker(d, staff_names)
			gm.write_to_file(name + " graph")

	
def get_metrics():
	path = "../grc/graphs/collab/"
	gnames = os.listdir(path)
	for name in gnames:
		if "University" not in name and "Inter School" not in name:
			with open(path + name) as f:
				data = json.load(f)
			g = json_graph.node_link_graph(data)
			gm = gfd.GraphMaker(g)
			# TODO commmenting this out for now
			#gm.add_metrics()
			gm.add_just_school_community()
			gm.write_to_file(path + name)

# TODO correct this
def add_school_info():
	nameurlpath = "../nameurls/"
	graphpath = "../grc/graphs/collab/"
	nufiles = os.listdir(nameurlpath)
	graphfiles = os.listdir(graphpath)
	allgraphs = []
	school_lists = {}
	for nufile in nufiles:
		schoolname = nufile.split(".")[0]
	
		with open(nameurlpath + nufile) as f:
			nameurls = json.load(f)
	
		just_urls = [nameurl[1] for nameurl in nameurls]
		school_lists[schoolname] = just_urls

	for gfile in graphfiles:
		if "University" in gfile or "Inter School" in gfile:
			continue

		with open(graphpath + gfile) as f:
			gdata = json.load(f)

		g = json_graph.node_link_graph(gdata)
		for author in g.nodes():
			found = False
			for school, urls in school_lists.items():
				if author == "http://eprints.gla.ac.uk/view/author/3545.html":
					g.node[author]["school"] = "School of Computing Science"
					found = True
				elif author in urls:
					found = True
					g.node[author]["school"] = school

			if not found:
				g.node[author]["school"] = False

		allgraphs.append(g)
	
		writedata = json_graph.node_link_data(g)
		with open(graphpath + gfile, 'w') as f:
			json.dump(writedata, f)

	unigraph = nx.compose_all(allgraphs)

	gm = gfd.GraphMaker(unigraph)
	gm.add_metrics()
	gm.write_to_file(graphpath + "The University of Glasgow.json")

	#unidata = json_graph.node_link_data(unigraph)
	#with open(graphpath + "The University of Glasgow.json", 'w') as f:
	#	json.dump(unidata, f)

def make_schools_graph():
	graphpath = "../grc/graphs/collab/"
	with open(graphpath + "The University of Glasgow.json") as f:
		data = json.load(f)

	unigraph = json_graph.node_link_graph(data)
	
	schoolnames = [sn.split(".")[0] for sn in os.listdir(graphpath) if "University" not in sn and "Inter School" not in sn]
	print schoolnames

	schools_graph = nx.Graph(graphname="SchoolsGraph")
	for schoolname in schoolnames:
		# NB node gets school name as id, but we are giving it a name attribute as well to work better with the javascript code
		schools_graph.add_node(schoolname, {"name":schoolname})
		print "added node", schoolname

	seen_pairs = set()

	for author in unigraph.nodes():
		school1 = unigraph.node[author]["school"]
		# TODO can't get num_papers from unigraph because not accurate.. 
		# this is because authors may be in several school graphs, and their num papers depends on if it is their own school or not
		# so their num papers attribute in the uni graph depends on which version of them was added last.
		# So for now not using num papers in inter schools graph
		for coauthor, edgeattribs in unigraph.edge[author].items():
			# Check if this pair of coauthors has been seen already so we don't duplicate num_collabs
			if (author, coauthor) in seen_pairs or (coauthor, author) in seen_pairs:
				continue

			school2 = unigraph.node[coauthor]["school"]
			# Attention author may have school attribute as false if not associated to any school
			if school1 == school2 or school1 == False or school2 == False:
				continue
			
			if schools_graph.has_edge(school1, school2):
				schools_graph[school1][school2]["num_collabs"] += edgeattribs["num_collabs"]
				# Check if papers are already in title_urls to avoid repetition
				for title_url in edgeattribs["collab_title_urls"]:
					if title_url not in schools_graph[school1][school2]["collab_title_urls"]:
						schools_graph[school1][school2]["collab_title_urls"].append(title_url)
	
			else:
				schools_graph.add_edge(school1, school2, {"num_collabs": edgeattribs["num_collabs"], "collab_title_urls": edgeattribs["collab_title_urls"]})

			seen_pairs.add((author, coauthor))


	gm = gfd.GraphMaker(schools_graph)
	gm.add_metrics()
	gm.write_to_file(graphpath + "Inter School.json")

	#writedata = json_graph.node_link_data(schools_graph)
	#with open(graphpath + "Inter School.json", "w") as f:
	#	json.dump(writedata, f)

	return schools_graph


def make_indices():
	data_path = ("../coauthor_data/")
	data_files = os.listdir(data_path)
	full_dict = {}
	for data_file in data_files:
		if "full" in data_file:
			continue

		with open(data_path + data_file) as f:
			dd = json.load(f)

		dd = textutils2.add_kw_to_data(dd)

		for title, data in dd.items():
			authors = data["authors"]
			newauthors = [(anu[0].split(", ")[1] + " " + anu[0].split(", ")[0], anu[1]) for anu in authors]
			dd[title]["authors"] = newauthors
		
		srch = search.Search()
		srch.make_index(dd)
		indx = srch.get_index()



		she = shelve.open("../grc/indices/invindex9.db")
		for term in indx:
		# 	if term == "programming":
		 #		print indx[term]
		 	if term in she:
		 		she[term] = she[term].union(indx[term])
		 	else:
		 		she[term] = indx[term]
	
		she.close()

		#akw_indx = srch.make_author_kw_index(dd)
		tkw_indx = srch.make_title_kw_index(dd)
		she = shelve.open("../grc/indices/titlekwindex2.db")
		#she.update(akw_indx)
		for title in tkw_indx:
			she[title] = tkw_indx[title]
			# if title in she:
			# 	she[author] += akw_indx[author]
			# else:
			# 	she[author] = akw_indx[author]
		she.close()

	# 	for term in indx:
	# 	 	if term in full_dict:
	# 	 		full_dict[term] = full_dict[term].union(indx[term])
	# 	 	else:
	# 	 		full_dict[term] = indx[term]

	# for term, papers in full_dict.items():
	# 	full_dict[term] = list(papers)


	# with open(data_path + "full.json", 'w') as f:
	# 	json.dump(full_dict, f)
	


#def make_akw():


if __name__ == "__main__":
	pass
	#get_and_graph()
	#graphs_from_files()