# just a test
# this goes through all the xml files made by tokentest
# parses them and extracts the titles, returns dict with author: [titles]

from lxml import etree
#import tokentest


def get_oai_dict(filename, numfiles):
	#xml_list = tokentest.get_xml_list()
	bib_dict = {}

	#tree = etree.parse("cs_test.xml")
	#root = tree.getroot()

	for i in range(1, numfiles+1):
		
		tree = etree.parse("../xml_files/" + filename + str(i) + ".xml")
		root = tree.getroot()
		print root

		records = root[2]

		for record in records:
			if len(record) and record[0].get("status") != "deleted":
				header = record[0]
				metadata = record[1]
				info = metadata[0]
				title = ""
				authors = []
				for elem in info:
					if "title" in elem.tag:
						title = elem.text
					if "creator" in elem.tag:
						authors.append(elem.text)

				# remove line breaks from title
				title = title.replace('\r\n', '')

				for author in authors:
					# split to separate last name and first name initials
					# then reconstruct name to have last name, first initial (only first initial to be consistent with scraping dict)
					tokens = author.split(" ")
					name = tokens[0] + " " + tokens[1][:1]
					if name in bib_dict:
						bib_dict[name].append(title)
					else:
						bib_dict[name] = [title,]

	return bib_dict


# print bib_dict
# with open("dicto.txt", 'w') as f:
# 	for key in bib_dict:
# 		f.write(key)
# 		for paper in bib_dict[key]:
# 			f.write(paper.encode("utf-8") + "  ")

			
