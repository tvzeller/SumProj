import re

# NB TODO this only works when node keys are the names, is that what we want?
def disambiguate(g):
	index_names = enumerate(g.nodes())
	similar_keys_dict = {}
	names = g.nodes()
	for i, n in index_names:
		base_name = make_base_name(n)

		if base_name not in similar_keys_dict:
			similar_keys_dict[base_name] = [n]
		
			for j in range(i+1, len(nodes)):				
				if base_name == make_base_name(nodes[j]):
					similar_keys_dict[base_name].append(nodes[j])
		else:
			continue

	for base_name, similar_keys in similar_keys_dict:
		if similar_keys > 1:
			compare_coauthors(g, similar_keys)

    # Testing
	return similar_keys_dict



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


def compare_coauthors(graph, keys):
	

