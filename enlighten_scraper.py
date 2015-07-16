# gets urls for enlighten author pages
# visits urls and makes dict with author: [titles]

# TODO consider making this a class to avoid passing around variables
# e.g. the name of the School, stafflist base URL could be instance variables
# ATTention school of humanities

import requests
from lxml import html
## TODO try other lxml modules instead of html
import time
import re
import json
import operator



def get_tree(url):
	while True:
		try:
			page = requests.get(url, timeout=10)
			time.sleep(3)
			tree = html.fromstring(page.text)
			break
		except requests.exceptions.Timeout:
			print "Request timed out, trying again..."
		except requests.exceptions.ConnectionError:
			print "requests connection error, trying again"
		except requests.exceptions.RequestException:
			print "ambiguous requests exception happened, trying again"

	return tree


def get_names(url):
	
	""" 
	returns list of name tuples in form [("last name", ", "title first name"), etc]
	e.g. [("Manlove", ", Dr David")]
	So join 2 together to get Manlove, Dr David 
	"""

	# get html element tree
	tree = get_tree(url)
	# get list of last names
	last_names = tree.xpath('//*[@id="research-teachinglist"]/li/a/strong/text()')
	# get list of (titled) first names
	titled_first_names = tree.xpath('//*[@id="research-teachinglist"]/li/a/text()')
	# make list of (last name, first name) tuples
	full_names = ["%s%s" % (first, last) for first, last in zip(last_names, titled_first_names)]
	#name_tups = zip(last_names, titled_first_names)
	print full_names
	return full_names


def get_author_url(author_list_url, author_name):
	""" 
	takes the base url for lists of Glasgow authors, and last and first name,
	returns the url for the page of the author with that name
	"""

	print "getting url for" + author_name
	# create full url based on the first initial of the author's last name
	# TODO consider doing this outside this method and just taking the full url as a parameter
	full_url = author_list_url + "index."+ author_name.split(" ")[0][0] + ".html"
	# get the html tree for the relevant author list page
	tree = get_tree(full_url)
	
	# concatenate last and first names and convert to lower case
	full_name = author_name.lower()
	
	# used to convert text in <a> tags to lower case in paths before checking if equals the name provided
	case = 'translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")'
	# uses full first name
	path = '//table/tr/td/ul/li/a[contains(%s, \"%s\")]' % (case, full_name)

	# get list of <a> elements whose text matches the name
	elements = tree.xpath(path)

	# this means that the name was found more than once on the page
	if len(elements) > 1:
		print "MORE THAN ONE ELEMENT"
	
	urls = []
	# if name was found, concatenate the href attribute obtained to the base url and return
	if elements:
		# have to concatenate as href is given as relative path
		urls = [(elem.text, author_list_url + elem.get("href")) for elem in elements]
		#url = author_list_url + elements[0].get("href")
		print urls
		print "GOT HERE"
	else:
		# create file of names that were not found to check for reasons why
		with open("unfound_names.txt", 'a') as f:
			f.write(author_name)

	return urls
		

def sort_name_urls(name_url_list, schl_name):
	# TODO this function should be called count school matches?
	school_matches = {}
	for name_url in name_url_list: # for each author page
		school_matches[name_url] = 0
		a_elems = get_a_elems(name_url[1]) # get paper <a> elements
		for a in a_elems:
			schl_info = get_paper_school_info(a.get("href"))
			# TODO do this by percentage of papers matching school instead of absolute value?
			if schl_name in schl_info:
				school_matches[name_url] += 1

	# Get list of (name, url) tuples sorted by number of matches
	# First Sort a list of (key, value) tuples ordered by item at index 1 (the value, i.e. the num of matches)
	# N.B. use reverse flag so that key with highest value goes first
	sorted_schl_matches = sorted(school_matches.items(), key=operator.itemgetter(1), reverse=True)
	# Then make list from just the keys (the (name, url) tuples)
	sorted_name_urls = [kv_tup[0] for kv_tup in sorted_schl_matches]

	return sorted_name_urls

def check_if_in_dept(author_url, schl_name):
	a_elems = get_a_elems(author_url)
	in_dept = False
	i = 0
	while not in_dept and i < len(a_elems):
		schl_info = get_paper_school_info(a_elems[i].get("href"))
		if schl_name in schl_info:
			in_dept = True
		else:
			i += 1

	return in_dept


def get_paper_school_info(paper_url):
	paper_tree = get_tree(paper_url)
	path = '//table/tr/th[text() = "College/School:"]/following-sibling::td/a/text()'
	school_info = paper_tree.xpath(path)
	# here have to check if schl_name is in any of the items of school_info (which may be more than one,
	# if paper is associated to more than one school)
	schl_info_string = "\n".join(school_info)

	return schl_info_string



def get_a_elems(url):
	tree = get_tree(url)
	ns = 'http://exslt.org/regular-expressions'
	path = '//a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]'
	a_elems = tree.xpath(path, namespaces={'re':ns})
	return a_elems



def initialise_first_name(name):
	"""
	takes full name in the form "Last Name, Title First Name" and returns 
	full name with the first name as an initial
	"""
	#tokens = first.split(" ")
	#first_tokens[2] = first_tokens[2][:1]
	#initial_first = " ".join(first_tokens)
	#return (last + initial_first)

	tokens = name.split(", ")
	last_name = tokens[0]
	first_tokens = tokens[1].split(" ")
	first_tokens[1] = first_tokens[1][0]
	return last_name + ', ' + " ".join(first_tokens)


def get_author_titles(author_url):
	"""
	Takes url of author page and returns a tuple with 2 elements.
	The first is a list of all the titles on the author's page, the second is
	a list of just the titles that have been tagged with a subject
	"""

	#tree = get_tree(author_url)
	#print "got here at least"

	# namespace for use with xpath regular expressions
	#ns = 'http://exslt.org/regular-expressions'

	# NOTE: THE BELOW HAS ALL BEEN FIXED BY USING TEXT_CONTENT()
	# n.b. double // before text() - this is to account for cases where the text is not directly
	# between the <a> tags, but has something in between like <strong> or <em>
	# AKA the Tango with Django exception
	# TODO TODO TODO http://stackoverflow.com/questions/10424117/xpath-expression-for-selecting-all-text-in-a-given-node-and-the-text-of-its-chl
	# because this doesn't work with <i> tags apparently see "Athorne, C" exception in maths
	# text_path = '//a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]//text()'
	# all_titles = tree.xpath(text_path, namespaces={'re':ns})

	# href_path = '//a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]/@href'
	# links = tree.xpath(href_path, namespaces={'re':ns})

	# instead of parsing once for the text and again for the hrefs
	# parse once only for the a elements, then extract the text and the href from the a elements
	#path = '//a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]'
	#a_elems = tree.xpath(path, namespaces={'re':ns})

	a_elems = get_a_elems(author_url)

	all_titles = []
	links = []
	# Loop through a elements and put associated href and text into respective lists
	for a in a_elems:
		all_titles.append(a.text_content())
		links.append(a.get("href"))

	# Create list of (title, url) tuples
	titles_links = zip(all_titles, links)
	# Get the list of titles of papers that have been tagged with a subject
	tagged_titles = get_tagged_titles(titles_links)

	#datestrings = tree.xpath('//div[@class="ep_view_page ep_view_page_view_author"]/p/text()[2]')
	# date will be in text at either at position 1 or 2 - this depends on whether authors include
	# a Glasgow author - if so, the author names will be in a <span> and will not be counted as p/text()
	# but will act as a delimiter - so what comes after it (in this case the date) is in position 2
	# otherwise, the authors will be text and so the date will be in position 1, as they come before any delimiter 
	#datestrings = tree.xpath('//div[@class="ep_view_page ep_view_page_view_author"]/p/text()[position() = 1 or position() = 2]')

	# OK this is the correct one for now
	# looks for the link to the paper then gets the text in the immediately preceding sibling node
	# should work as the date is always right before the title of the paper
	# datestrings = tree.xpath('//div[@class="ep_view_page ep_view_page_view_author"]/p/a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]/preceding-sibling::text()[1]', 
	# 				namespaces={'re':ns})
	# dates = []
	# for datestring in datestrings:
	# 	date = re.findall('[0-9]+', datestring)
	# 	# findall returns list of strings that match pattern (i.e. numbers)
	# 	if date:
	# 		dates.append(date[0])

	# Remove full stops from end of titles
	all_titles = [title[:-1] if title[-1] == '.' else title for title in all_titles]
	tagged_titles = [title[:-1] if title[-1] == '.' else title for title in tagged_titles]
	# use loop instead of list comprehension?
	# TODO or get rid of this since we are now comparing titles from same data set?

	#title_dates = zip(titles, dates)

	return (all_titles, tagged_titles)
	#return all_titles

def get_tagged_titles(ttls_lnks):
	"""
	Given a list of titles and urls, returns a list with the titles of just the
	those papers which have been tagged with a subject
	"""
	tagged_titles = []
	for title, link in ttls_lnks:
		print "checking" + title.encode("utf-8")
		paper_tree = get_tree(link)
		path = '//table/tr/th[text() = "Subjects:"]'
		subject_th = paper_tree.xpath(path)
		if subject_th:
			tagged_titles.append(title)

	return tagged_titles


def get_scrape_dict(dept_url, dept_name):
	"""
	Given a url with staff list, returns a dict with author names as keys
	and 2-element tuples as values. The first element is a list of all
	the papers, the second is a list of just the papers that have been tagged 
	"""

	# Change to "School of Humanities" to match the name used in Enlighten
	if "Humanities" in dept_name:
		dept_name = "School of Humanities"

	search_url = "http://eprints.gla.ac.uk/cgi/search"

	# TODO should this be a global variable?
	author_list_base = "http://eprints.gla.ac.uk/view/author/"

	bib_dict = {}

	# get list of names of researchers in department
	names = get_names(dept_url)

	# loop through each name
	for name in names:
		name_url = get_winning_url(author_list_base, name, bib_dict.keys(), dept_name)
		if name_url:
			titles = get_author_titles(name_url[1])
			bib_dict[name_url] = titles


	with open('subj_dicts/' + dept_name + ".txt", 'w') as f:
		json.dump(bib_dict.items(), f)

	# TO RESTORE from JSON
	# dict(map(tuple, kv) for kv in json.loads("file"))
	# converts each element in the JSON list of lists to tuples using map
	# then converts resulting tuples to dictionary
	# http://stackoverflow.com/a/12338024
	# http://stackoverflow.com/questions/12337583/saving-dictionary-whose-keys-are-tuples-with-json-python

	return bib_dict

# There is a list of authors on each school staff page; we are looking for each of their names amongst the names of
# all the authors on Enlighten (University wide system). One problem is that the name on the staff page
# may not be the same as the name on Enlighten - because of nicknames, misspellings etc.
# To make sure we find the person, we abbreviate their first name to one initial, keeping their full last name
# and title. This may get us several candidate names, so we choose the one who has most papers associated to the
# school they are supposed to be in. The chosen name may very well be someone else in the same department who happened
# to have more papers. But then when their own name is searched for, it will be abbreviated and the original author
# will come up in the set of candidates again. Since (name, url) pairs that are already present are filtered out,
# the original author will be first in the number of papers in school ranking and will be placed in the dict this time (hopefully).
# This way everyone is accounted for.

# EXAMPLE
# There are 2 people, A and B, that are listed on CS staff page and whose names abbreviate to "Wilson, Dr J".
# They are both on Enlighten, along with 2 other authors C and D whose names also abbreviate to "Wilson, Dr J".
# A is searched for first, giving us 4 candidate (name, url) pairs.
# We sort them by number of papers associated to CS and B comes out on top - her (name, url) tuple is used.
# We then search for B, again giving us the same 4 candidates. Since B is found to already be in the dict,
# we sort the remaining authors (A, C and D), with A coming out on top as she has more papers in CS.
# Thus A is now put in the dict and both A and B are now included, even if they were placed in a different
# order to how they are listed on the staff page.

# Notes:
# Assumption is that the academic title of authors is consistent across staff page and Enlighten.
# Ranks likelihood of being in department by number of papers associated to the department - other measures could
# be used (number of coauthors in department for instance).

# Other strategies to consider here - string similarity measures instead of using abbreviated names.
# This would avoid some name clashes (which would still happen if people had exact same names) but 
# would be more complicated.

def get_winning_url(authors_base_url, name, existing_authors, school):
	# abbreviate name
	abbr_name = initialise_first_name(name)
	# Get all the urls which match the author's name
	urls = get_author_url(authors_base_url, abbr_name)
	
	# If urls were found, remove the (name, url) pairs that are already present in the dict
	if urls:
		for name_url in urls:
			if name_url in existing_authors:
				urls.remove(name_url)

	# There is still more than one possible author so have to pick one of them
	# Pick the one with most papers associated to the relevant school
	if len(urls) > 1:
		# Sort (name, url) pairs by number of papers in relevant school
		sorted_urls = sort_name_urls(urls, school)
		# The first one in the list is chosen 
		# TODO FIRST CHECK IF SOMEONE ACTUALLY HAS PAPERS ASSOCIATED - BECAUSE MAYBE NONE OF THEM ARE IN DEPT
		# THIS IS IMPORTANT
		winning_name_url = sorted_urls[0]
		print "CLASH! Winner is", winning_name_url[0]

	# After the existing (name, url) pairs have been filtered out, there is only one url present
	# If match has been made with abbreviated first name, there is a chance that the author we were looking
	# for is not present in Enlighten, and we have someone not in the right dept, so check if they are in the
	# right dept before accepting them
	elif len(urls) == 1:
		print "WAIT...checking if in the right department"
		# Check their papers to see if associated to right department
		# TODO is this step necessary? More accurate results but adds quite a bit of time as more
		# requests have to be made
		is_in_dept = check_if_in_dept(urls[0][1], school)
		if is_in_dept:
			print "yes, proceed"
			winning_name_url = urls[0]
		# Probably not in right department, reject
		else:
			winning_name_url = None

	# No (name, url) pairs returned
	else:
		print name + " not found"
		winning_name_url = None

	print "name is " + name + " now returning"
	return winning_name_url


def getKeys(d, last_name):
	keys = []
	for key in d.keys():
		if last_name in key[0]:
			keys.append(key)
	return keys