import englighten_scraper as es
import text_utils as tu
import graph_utils as gu

def get_data_dicts():
	data_dicts = []
	author_name_urls_list = []
	school_data = {}
	school_name_urls = es.get_school_name_urls()
	for schoolname, schoolurl in school_name_urls:
		author_name_urls = es.get_author_name_urls(schoolname, schoolurl)
		data_dict = es.get_coauthors_dict(author_name_urls, schoolname)
		#data_dicts.append(data_dict)
		#author_name_urls_list.append(author_name_urls)
		school_data[schoolname] = (data_dict, author_name_urls)

	#data_schoolauthors = zip(data_dicts, author_name_urls_list)
	return school_data

def make_school_graphs(school_data):
	school_graphs = {}
	for schoolname, data in school_data.items():
		data_dict = data[0]
		school_authors = data[1]
		cgm = gu.CollabGraphMaker()
		cgm.populate_graph(data_dict, schoolauthors)
		graph = cgm.get_graph()
		graph = gu.add_metrics(graph)
		graph = add_just_school_community(graph)
		school_graphs[schoolname] = graph

	return school_graphs


def make_indices(data_dicts):
	for dd in data_dicts:
		dd_with_kw = tu.add_kw_to_data(dd)
		index = tu.make_index(dd_with_kw)

		stored_index = shelve.open("../indices/invindex.db")
		for term in index:
			if term in stored_index:
				stored_index[term] = stored_index[term].union(index[term])
			else:
				stored_index[term] = index[term]

		pkw_index = tu.make_paper_kw_index(dd_with_kw)
		stored_pkw = shelve.open("../indices/paperkwindex.db")
		for paper_id in pkw_index:
			stored_pkw[paper_id] = pkw_index[paper_id]

		stored_pkw.close()

def correct_author_names(dd):
	for paper_id, info in dd.items():
		authors = info['authors']
		newauthors = [(anu[0].split(", ")[1] + " " + anu[0].split(", ")[0], anu[1]) for anu in authors]
		dd[paper_id]['authors'] = newauthors


	return dd

def get_author_kw_dicts(data_dicts):
	#akws = {}
	school_akws = {}
	dds_with_kws = tu.get_data_with_keywords(data_dicts)
	akws = tu.make_author_kw_dicts(dds_with_kws)
	for school, akw in zip(school_data.keys(), akws):
		school_akw[school] = akw

	return school_akws

def make_sim_graphs(school_graphs, school_akws):
	school_simgraphs = {}
	for school in school_graphs:
		collab_graph = school_graphs[school]
		akw = school_akws[school]
		sim_graph = gu.make_sim_graph(akw, collab_graph)
		school_simgraphs[school] = sim_graph

	return school_simgraphs

def add_com_keywords_to_graphs(school_graphs, school_akws):
	for school, graph in school_graphs.items():
		akw = school_akws[school]
		graph_with_kw = gu.add_com_keywords(akw, graph)
		school_graphs[school] = graph_with_kw

	return school_graphs


if __name__ == "__main__":
	school_data = get_data_dicts()
	for school, data in school_data.items():
		data_dict = data[0]
		correct_names_dict = correct_author_names(data_dict)
		author_name_urls = data[1]
		school_data[school] = (correct_names_dict, author_name_urls)

	school_graphs = make_school_graphs(school_data)

	just_data_dicts = [data[0] for data in school_data.values()]
	
	make_indices(just_data_dicts[:])

	author_kw_dicts = get_author_kw_dicts(just_data_dicts[:])

	sim_graphs = make_sim_graphs(school_graphs, author_kw_dicts)

	school_urls = {}
	for school, data in school_data.items():
		name_urls = data[1]
		just_urls = [name_url[1] for name_url in name_urls]
		school_urls[school] = just_urls

	school_graphs = add_school_info(school_graphs, school_urls)

	unigraph = gu.make_unigraph(school_graphs.values())
	school_names = school_data.items()
	interschool_graph = gu.make_interschool_graph(school_names, unigraph)
	
	school_graphs = add_com_keywords_to_graphs(school_graphs, school_akws)

	collab_graph_path = "../graphs/collab/"
	for schoolname, graph in school_graphs.items():
		path = collab_graph_path + schoolname + ".json"
		gu.write_to_file(graph, path)

	unipath = collab_graph_path + "The University of Glasgow.json"
	gu.write_to_file(unigraph, unipath)

	interpath = collab_graph_path + "Inter School.json"
	gu.write_to_file(interschool_graph, interpath)

	sim_graph_path = "../graphs/simiilarity/"
	for schoolname, sim_graph in sim_graphs:
		path = sim_graph_path + schoolname + ".json"
		gu.write_to_file(sim_graph, path)



















