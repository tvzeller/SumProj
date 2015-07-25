import re


def disambiguate(g):
	index_authors = enumerate(g.nodes())
	similar_keys_dict = {}
	for i, author in index_authors:
		base_name = make_base_name(author)
		if base_name not in similar_keys_dict:
			similar_keys_dict[base_name] = [author]
		for j in range(i+1, len(g.nodes())):				
			if base_name == make_base_name(g.nodes()[j]):
				similar_keys_dict[base_name].append(g.nodes()[j])
    # Testing
	return similar_keys_dict



# NB this works for Last Name, Title First Name
# Need one for Last Name, Initials (as in OAI data)
# And what about Last Name, First Name (no title)?? TODO
# How can you tell the difference between that and a name with title??
def make_base_name(name):
	# TODO use regex here to check if name contains ", [letter].", which would indicate the presence of an initialised first name with no title
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
