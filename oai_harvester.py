# gets papers from url (tagged in subset)
# uses resumptionTokens to get all the papers
# puts each response in a separate xml file

import requests
import xml.etree.ElementTree as ET
# TODO use lxml etree instead
import time

url = "http://eprints.gla.ac.uk/cgi/oai2"
#sub_set = "7375626A656374733D51:5141:51413735"

def get_it(response, l, i, filename):
	print response.content
	print "ABOVE IS THE SUPPOSED FIRST RESPONSE"
	i += 1
	token = ""
	#root = ET.fromstring(response.text.encode("utf-8"))
	print "looking for token in " + str(i-1)
	root = ET.fromstring(response.content)
	for child in root[2]:
		if 'resumptionToken' in child.tag:
			token = child.text
			print "token for " + str(i-1) + " is " + token
		else:
			print "no token found in " + str(i-1)

	if token:
		newresponse = requests.get(url + "?verb=ListRecords&resumptionToken=" + token)
		#fl.write(newresponse.text.encode("utf-8"))
		#fl.write(newresponse.content)
		#xml_string += newresponse.text.encode("utf-8")
		l.append(newresponse.content)
		with open("xmlfile" + filename + str(i) + ".xml", 'w') as f:
			f.write(newresponse.content)

		get_it(newresponse, l, i, filename)
	else:
		print "no resumption token, returning..."
		return
		

def get_xml_list(sub_set, filename):
	start_time = time.time()
	xml_list = []
	index = 1
	
	response = requests.get(url + "?verb=ListRecords&set=%s&metadataPrefix=oai_dc" % sub_set)
	xml_list.append(response.content)
	print response.text.encode("utf-8")
	with open("xmlfile" + filename + str(index) + ".xml", 'w') as f:
		f.write(response.content)

	get_it(response, xml_list, index, filename)
	
	time_taken = time.time() - start_time
	print "time taken was %f seconds so around %f minutes" % (time_taken, time_taken/60)

	return xml_list



subjects = [()]

#glafile = open('cs_test.xml', 'a')
#glafile.write(response.text.encode("utf-8"))
#glafile.write(response.content)
#get_it(response, glafile)	
#print xml_string

#get_xml_list()	




		
		