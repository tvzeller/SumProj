# gets urls for enlighten author pages
# visits urls and makes dict with author: ([all_titles][tagged_titles])

# TODO consider making this a class to avoid passing around variables
# e.g. the name of the School, stafflist base URL could be instance variables
# ATTention school of humanities

# TODO write tests for this
# TODO refactor

import requests
import lxml
from lxml import html
## TODO try other lxml modules instead of html
import time
import re
import json
import operator
import sys
import re

# Base url for list of authors on Enlighten
author_list_base = "http://eprints.gla.ac.uk/view/author/"
# Amount of time in seconds request waits for response before giving up and throwing exception
TIMEOUT = 15
# Amount of requests exceptions scraper gets before shutting down
MAX_EXCEPTIONS = 15
# Amount of time in seconds between requests
SLEEP_TIME = 0.8

def get_tree(url):
	"""
	Takes a url and returns an html tree object to be parsed using
	lxml
	"""
	num_exceptions = 0
	while True:
		time.sleep(SLEEP_TIME)
		try:
			page = requests.get(url, timeout=TIMEOUT)
			try:
				tree = html.fromstring(page.text)
			except lxml.etree.XMLSyntaxError:
				return False
			break
		except requests.exceptions.Timeout:
			print "Request timed out, trying again..."
		except requests.exceptions.ConnectionError:
			print "requests connection error, trying again"
		except requests.exceptions.RequestException:
			print "ambiguous requests exception happened, trying again"
		num_exceptions += 1
		# If we hit too many exceptions, exit program
		if num_exceptions == MAX_EXCEPTIONS:
			sys.exit()

	return tree

def get school_name_urls():
	"""
	gets a list of (school name, url of staff page) tuples from the Glasgow University website
	"""
	schools_tree = get_tree("http://www.gla.ac.uk/schools/")
	ns = 'http://exslt.org/regular-expressions'
	path = '//div[@class="row standardContent"]//a[re:match(@href, "schools/[A-Za-z]+/")]'
	# Get all the <a> elements on the page which link to a school page
	a_elems = schools_tree.xpath(path, namespaces={'re':ns})
	base_url = "http://www.gla.ac.uk"
	urls = []
	names = []

	for a in a_elems:
		# make school staff page url
		staff_page_url = base_url + a.get("href") + "staff/"
		urls.append(staff_page_url)
		# get name of school
		school_name = a.text
		names.append(school_name)

	# create list of tuples
	school_names_urls = zip(names, urls)
	return school_names_urls


def get_names(url):
	
	""" 
	returns list of names in form "Last Name, Title First Name"
	e.g. "Manlove, Dr David"
	"""
	# get html element tree
	tree = get_tree(url)
	# Names are text within <a> elements in this list
	# xpath returns a list with alternating last and first names as elements
	# Concatenate each last name and first name pair and put in new list as full name
	names = tree.xpath('//*[@id="research-teachinglist"]/li//a//text()')
	full_names = []
	for i in range(0, len(names)-1, 2):
		full_names.append(names[i] + names[i+1])

	return full_names

	
	
def get_name_url_matches(author_name, html_tree):
	"""
	Takes an author name and the html tree of the page on which to look for their name.
	Returns a list of (name, author page url) tuples, each an author which matched the searched name
	"""

	# Convert name to lower case - this will be searched against lower case text on the Enlighten page
	lower_name = author_name.lower()
	# Used to convert text in <a> tags to lower case in paths before checking if matches the name provided
	case = 'translate(text(), "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")'
	# This is the path to look for <a> tags which contain the target name as text
	# N.B. contains() is used rather than equals as it can catch more cases
	path = '//table/tr/td/ul/li/a[contains(%s, \"%s\")]' % (case, lower_name)
	# get the list of <a> elements whose text contains the name
	elements = html_tree.xpath(path)
	# If target string was found, for each <a> element that contains it, make a
	# (text, url) tuple and create a list out of the resulting tuples
	# N.B. the href obtained from the element is concatenated to the base url as it is relative
	if elements:
		# have to concatenate as href is given as relative path
		text_url_tups = [(elem.text, author_list_base + elem.get("href")) for elem in elements]
	else:
		text_url_tups = None

	return text_url_tups
		

def sort_name_urls(name_url_list, schl_name):
	"""
	Takes a list of (author name, author page url) tuples and the name of the school the author is
	supposed to be in.
	Returns a list of (name, url) tuples sorted by the amount of papers each author has that is
	associated to the given school
	"""

	# A dict to have (name, url) tuples as keys and the amount of papers in the relevant school
	# as values
	school_matches = {}

	for name_url in name_url_list: # for each author page
		school_matches[name_url] = 0
		author_page_tree = get_tree(name_url[1])
		# get the <a> elements for each paper on the author's page
		a_elems = get_a_elems_for_papers(author_page_tree)
		for a in a_elems: # for each paper
			# from the paper's Enlighten page, get a string indicating what school it is associated to
			schl_info = get_paper_school_info(a.get("href"))
			# If the relevant school is found in the school info string, increment the value
			# of this (name, url) key
			if schl_name in schl_info:
				school_matches[name_url] += 1

	# From dict, create list of ((name, url), numpapers) tuples sorted by value
	sorted_name_urls = sorted(school_matches.items(), key=operator.itemgetter(1), reverse=True)	

	return sorted_name_urls

def check_if_in_dept(author_url, schl_name):
	"""
	Takes the url for an author page on Enlighten and the name of a school and 
	checks if author has at least one paper associated to the given school 
	"""
	# Get list of the <a> elements linking to all the papers on the author's page
	author_page_tree = get_tree(author_url)
	a_elems = get_a_elems_for_papers(author_page_tree)
	in_dept = False

	for a_elem in a_elems:
		# For each paper, get the school info for that paper
		schl_info = get_paper_school_info(a_elems.get("href"))
		# If the given school name is in the school info string, make in_dept True
		# and exit loop
		if schl_name in schl_info:
			in_dept = True
			break

	return in_dept


def get_paper_school_info(paper_url):
	"""
	Each paper on Enlighten is associated to one or more schools within the University.
	This function takes the url for the paper page and returns a string indicating
	which school(s) the paper is associated to
	"""

	paper_tree = get_tree(paper_url)
	# XPath to extract the school info
	path = '//table/tr/th[text() = "College/School:"]/following-sibling::td/a/text()'
	# This gives us a list of strings with school info (a paper may be associated to more than one school)
	school_info = paper_tree.xpath(path)
	# Join list to return the information as a single string string
	schl_info_string = "\n".join(school_info)

	return schl_info_string


def get_a_elems_for_papers(tree):
	"""
	Takes the html tree for an Enlighten author page and extracts the <a> elements which link
	to the papers on that page
	Returns list of those <a> elements
	"""

	ns = 'http://exslt.org/regular-expressions'
	path = '//a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]'
	a_elems = tree.xpath(path, namespaces={'re':ns})
	return a_elems


def get_dates_for_papers(tree):
	"""
	takes html tree for Enlighten author page and returns a list of dates (years) of all papers
	listed on page, in the order in which they are listed
	"""
	ns = 'http://exslt.org/regular-expressions'
	path = '//a[re:match(@href, "http://eprints.gla.ac.uk/[0-9]+/")]/preceding-sibling::text()'
	# gets a list of strings, each containing a date of a paper (amongst other irrelevant characters)
	text_containing_dates = tree.xpath(path, namespaces={'re':ns})
	# join the list into a single string so that regular expression can be used on it
	text_as_string = " ".join(text_containing_dates)
	# extract the dates from the string into a list
	dates = re.findall("[0-9]+", text_as_string)
	return dates


def initialise_first_name(name):
	"""
	takes full name in the form "Last Name, Title First Name" and returns 
	full name with the first name as an initial
	"""
	# Split name on the comma and space
	tokens = name.split(", ")
	last_name = tokens[0]
	# Split tokens[1] which is a "Title First Name" string
	first_tokens = tokens[1].split(" ")
	# Replace the first name with just the first initial
	first_tokens[1] = first_tokens[1][0]
	# Concatenate everything back together and return
	return last_name + ', ' + " ".join(first_tokens)



def get_author_titles(author_url):
	"""
	Takes url of author page and returns a tuple with 2 elements.
	The first is a list of all the titles on the author's page, the second is
	a list of just the titles that have been tagged with a subject, so
	([all_titles][tagged_titles])
	Note: this was used for investigating coverage statistics (amount of author's papers that are tagged)
	"""
	# Get the html tree for the author page
	author_page_tree = get_tree(author_url)
	# Get the <a> elements for the papers on the author's page
	a_elems = get_a_elems_for_papers(author_page_tree)

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
	# Return the 2 lists in a tuple
	return (all_titles, tagged_titles)


def get_tagged_titles(ttls_lnks):
	"""
	Given a list of (title, url) tuples, returns a list with the titles of just
	those papers which have been tagged with a subject
	Checks for tag by checking if the paper's page has a Subject row in information table
	"""
	tagged_titles = []
	for title, link in ttls_lnks:
		# TODO for testing, remove this later
		print "checking" + title.encode("utf-8")
		# get the html tree for the paper's page
		paper_tree = get_tree(link)
		path = '//table/tr/th[text() = "Subjects:"]'
		# Check if html contains the table header "Subjects:"
		subject_th = paper_tree.xpath(path)
		# If it does, this means paper is tagged so add to the list to be returned
		if subject_th:
			tagged_titles.append(title)

	return tagged_titles


def get_author_name_urls(dept_name, dept_url):
	"""
	Given a url with staff list, gets the Enlighten urls of the authors on the staff list.
	Returns as a list of (author name, author page url) tuples
	"""
	# Change to "School of Humanities" to match the name used in Enlighten
	# Done because the string obtained from http://www.gla.ac.uk/schools/ contains the Gaelic name as well
	if "Humanities" in dept_name:
		dept_name = "School of Humanities"

	# get list of names of researchers in department
	names = get_names(dept_url)

	winning_name_urls = set()

	# loop through each name
	for name in names:
		name = initialise_first_name(name)
		# Get Enlighten page on which author name will be found (page for the letter of author's last name)
		full_url = author_list_base + "index."+ name.split(" ")[0][0] + ".html"
		tree = get_tree(full_url)
		# Get all candidate authors which match the name
		name_urls = get_name_url_matches(name, tree)
		# If candidates were found
		if name_urls:
			# Filter out authors that have already been scraped
			name_urls = [name_url for name_url in name_urls if name_url not in winning_name_urls]
			# Get the first ranked (name, url) tuple for the target name from the remaining candidates
			winning_name_url = get_winning_url(name_urls, dept_name)
			if winning_name_url:
				winning_name_urls.add(winning_name_url)

	return winning_name_urls

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
def get_winning_url(nm_url_list, school):
	# If more than one candidate, have to pick one of them
	# Pick the one with most papers associated to the relevant school
	if len(nm_url_list) > 1:
		# Sort (name, url) pairs by number of papers in relevant school
		sorted_urls = sort_name_urls(nm_url_list, school)
		# Get back list of two element tuples - ((name, url), num_papers)
		# If the first ranked (name, url) has 0 num_papers in relevant school, disregard it
		if sorted_urls[0][1] == 0:
			winning_name_url = None
		# Else select the first ranked (name, url) as the winning_name_url
		else:
			winning_name_url = sorted_urls[0][0]

	# After the existing (name, url) pairs have been filtered out, there may be only one url present
	# If match has been made with abbreviated first name, there is a chance that the author we were looking
	# for is not present in Enlighten, and we have someone not in the right dept, so check if they are in the
	# right dept before accepting them
	elif len(nm_url_list) == 1:
		# Check their papers to see if associated to right department
		is_in_dept = check_if_in_dept(nm_url_list[0][1], school)
		if is_in_dept:
			winning_name_url = nm_url_list[0]
		# Otherwise probably not in right department, reject
		else:
			winning_name_url = None

	# No (name, url) pairs exist after already scraped authors have been filtered out
	else:
		winning_name_url = None

	return winning_name_url


def get_titles_dict(name_url_list):
	"""
	Given a list of (name, author page url), returns a dict keyed by author (name, url), with the values
	tuples of [all titles, tagged titles] - used for tagging coverage testing
	"""
	bib_dict = {}
	
	for name_url in name_url_list:
		titles = get_author_titles(name_url[1])
		bib_dict[name_url] = titles

	return bib_dict

def get_coauthors_dict(name_url_list, schl_name):
	""" 
	Given a list of (name, author page url) pairs, returns a dict keyed by the Enlighten id's of the papers
	written by each of the authors, with the paper's metadata as values.
	This is the main data structure returned by the scraper, and is used by the rest of the application to make
	the graphs, etc.
	"""

	paper_info_dict = {}

	for name_url in name_url_list:
		# Get a sub papers_info dictfor an individual author
		papers_info = get_papers_info(name_url[1], paper_info_dict.keys())
		# add sub dict to full dict
		paper_info_dict.update(papers_info)
	
	if "Humanities" in schl_name:
		schl_name = "School of Humanities"

	return paper_info_dict


def get_papers_info(author_url, existing_papers):
	"""
	Takes an author url and returns dict keyed by their papers' ids with paper metadata as values.
	Also takes a list of paper ids already in the full dict to avoid scraping data for those papers again.
	"""

	author_dict = {}

	author_page_tree = get_tree(author_url)
	# Get the <a> elements for the papers on the author's page
	a_elems = get_a_elems_for_papers(author_page_tree)
	# get the dates corresponding to each paper
	paper_dates = get_dates_for_papers(author_page_tree)
	# zip into a list of (a_elem, date) pairs
	a_elem_dates = zip(a_elems, paper_dates)
	# Each a is a paper
	for a, date in a_elem_dates:
		# Title of paper is the text content of the a element
		paper_title = a.text_content()
		# Check if paper has already been checked, if so, move on to next paper
		if paper_title in existing_papers:
			continue

		paper_url = a.get("href")

		paper_tree = get_tree(paper_url)
		# Get list of the paper's authors
		authors = get_paper_authors(paper_tree)
		# Get paper abstract
		abstract = get_paper_abstract(paper_tree)
		# Get paper keywords
		keywords = get_paper_keywords(paper_tree)
		# Get paper id number from its url
		paper_id = re.search("[0-9]+", paper_url).group()
		# Add paper to dictionary with id as key and metadata as values
		author_dict[paper_id] = {
						"title": paper_title,
						"authors": authors,
						"abstract": abstract,
						"url": paper_url,
						"keywords": keywords,
						'year': date
		} 

	return author_dict


def get_paper_authors(tree):
	"""
	Takes the html tree of the enlighten page of a paper and returns a list of the paper's coauthors
	in (author name, author page url) form
	"""
	path = '//table/tr/th[text() = "Glasgow Author(s) Enlighten ID:"]/following-sibling::td/a'
	# Get list of <a> elements, each an author
	authors = tree.xpath(path)
	# Make list of (author name, author url) pairs to return
	authors = [(author.text, author.get("href")) for author in authors]

	return authors


def get_paper_abstract(tree):
	"""
	Takes the html tree of the enlighten page of a paper and returns the abstract as a string
	"""
	path = '//h2[text() = "Abstract"]/following-sibling::p/text()'
	abstract = tree.xpath(path)
	# If paper page contains the abstract, xpath returns a list with single string element
	# Access list to get the abstract string to return
	if abstract and abstract[0] != "No abstract available.":
		abstract = abstract[0]
	
	return abstract


def get_paper_keywords(tree):
	"""
	Takes the html tree of the enlighten page of a paper and returns a list of the paper's keywords (if they
	have been added in Enlighten)
	"""
	path = '//table/tr/th[text() = "Keywords:"]/following-sibling::td/text()'
	keywords = tree.xpath(path)
	# xpath returns a list with the keywords as a single string element separated by whitespace, commas or semi-colons
	# Make this into a list of keywords
	if keywords:
		# Split on white space, commas and semi-colons
		keywords = re.split('[\s,;]', keywords[0])
		# Remove trailing white space and empty strings
		keywords = [kw.strip() for kw in keywords if kw]

	return keywords
