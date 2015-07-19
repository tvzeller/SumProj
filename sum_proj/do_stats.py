import requests
from lxml import html
import enlighten_scraper as es
import cvg_stats as cs
import sys

schools_tree = st2.get_tree("http://www.gla.ac.uk/schools/")
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

start_index = int(sys.argv[1])
end_index = int(sys.argv[2])

# TODO REMOVE SLICING
# THIS is temporary to just do the schools we haven't done yet
for schl_name, schl_url in school_names_urls[start_index:end_index]:
	
	author_name_urls = es.get_author_name_urls(schl_url, schl_name)
	titles_dict = es.get_titles_dict(author_name_urls)
	stats = cs.Stats(authors_dict, name)
	stats.write_to_file("stats_results/stats_test.txt")




