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

def correct_author_names(data_dicts):
	for dd in data_dicts:
		for paper_id, info in dd.items():
			authors = info['authors']
			newauthors = [(anu[0].split(", ")[1] + " " + anu[0].split(", ")[0], anu[1]) for anu in authors]
			dd[paper_id]['authors'] = newauthors


	return data_dicts

def get_author_kw_dicts(school_data):
	#akws = {}
	school_akws = {}
	all_data_dicts = [data[0] for data in school_data.values()]
	dds_with_kws = tu.get_data_with_keywords(all_data_dicts)
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












