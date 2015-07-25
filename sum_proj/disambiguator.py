import re

# NB TODO this only works when node keys are the names, is that what we want?
def get_similar_keys(g):
	index_names = enumerate(g.nodes())
	similar_keys_dict = {}
	names = g.nodes()
	for i, n in index_names:
		base_name = make_base_name(n)

		if base_name not in similar_keys_dict:
			similar_keys_dict[base_name] = [n]
		
			for j in range(i+1, len(names)):				
				if base_name == make_base_name(names[j]):
					similar_keys_dict[base_name].append(names[j])
		else:
			continue

    # Testing
	return similar_keys_dict

def disambiguate(g, skd):
	merged_authors = {}
	for base_name, similar_keys in skd.items():
		if similar_keys > 1:
			merged_authors.update(merge_authors(g, similar_keys))

	for k_author, v_author in merged_authors.items():
		k_coauthors = g[k_author]
		v_coauthors = g[v_author]

		for coauthor in v_coauthors:
			if coauthor in k_coauthors:
				k_coauthors[coauthor]["num_collabs"] += v_coauthors[coauthor]["num_collabs"]
				k_coauthors[coauthor]["collab_titles"].extend(v_coauthors[coauthor]["collab_titles"])
			else:
				g.add_edge(k_author, coauthor)
				g[k_author][coauthor]["num_collabs"] = v_coauthors[coauthor]["num_collabs"]
				g[k_author][coauthor]["collab_titles"] = v_coauthors[coauthor]["collab_titles"]

		g.remove_node(v_author)

	return g



def merge_authors(graph, keys):
	merged = {}
	# keys is a list of similar keys we need to disambiguate
	for index, name in enumerate(keys):
		if name in merged:
			continue

		coauthor_set = set(graph[name].keys())
		for j in range(index + 1, len(keys)):
			coauthors = set(graph[keys[j]].keys())
			common_coauthors = compare_coauthors(name, coauthor_set, coauthors)
			
			if common_coauthors:
				merged[keys[j]] = name
				coauthor_set.update(coauthors)

	return merged





# NB this works for Last Name, Title First Name
# Need one for Last Name, Initials (as in OAI data)
# And what about Last Name, First Name (no title)?? TODO
# How can you tell the difference between that and a name with title??
def make_base_name(name):
	# TODO use regex here to check if name contains ", [letter].", which would indicate the presence of an initialised first name with no title
	# TODO consider cases where name is First Name Last Name as well - see paper for ideas
	initials_match = re.search(", [a-zA-Z]\.", name)
	if initials_match:
		tokens = name.split(", ")
		# base name becomes Last Name, First Initial only
		base_name = tokens[0] + ", " + tokens[1][0]
	else:
		tokens = name.split(", ")
		first_name_tokens = tokens[1].split(" ")
		if len(first_name_tokens) < 2:
			abbrev_first_name = first_name_tokens[0][0]
		else:
			abbrev_first_name = first_name_tokens[0] + " " + first_name_tokens[1][0]
		# base name becomes Last Name, Title First Initial only
		base_name = tokens[0] + ", " + abbrev_first_name
	
	return base_name.lower()


def compare_coauthors(name, set1, set2):
	if name in set2:
		return False

	for author in set1:
		if author in set2:
			return True

	return False



