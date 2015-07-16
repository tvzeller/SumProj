# gets papers from url (tagged with the given subset)
# uses resumptionTokens to get all the papers
# puts each response in a separate xml file

import requests
import xml.etree.ElementTree as ET
# TODO use lxml etree instead
import time

url = "http://eprints.gla.ac.uk/cgi/oai2"
#sub_set = "7375626A656374733D51:5141:51413735"
		

def get_xml_list(sub_set, filename):
	start_time = time.time()
	xml_list = []
	index = 1
	
	# use the OAI-PMH ListRecords verb for the given set to get the first response
	response = requests.get(url + "?verb=ListRecords&set=%s&metadataPrefix=oai_dc" % sub_set)
	# Add the xml response to the list of responses
	xml_list.append(response.content)


	print response.text.encode("utf-8")
	# Write response to file TODO for testing purposes
	with open("../xml_files/" + filename + str(index) + ".xml", 'w') as f:
		f.write(response.content)

	has_resumption_token = True
	while has_resumption_token:
		index += 1
		
		token = check_for_res_token(response)

		if token:
			# Make new OAI-PMH request using resumption token
			response = requests.get(url + "?verb=ListRecords&resumptionToken=" + token)
			print response.text.encode("utf-8")
			# append the response to the list of xml responses
			xml_list.append(response.content)
			# Write response to file
			# TODO this is mostly for testing purposes
			with open("../xml_files/" + filename + str(index) + ".xml", 'w') as f:
				f.write(response.content)
		# If token was not found, change has_resumption_token to false to exit loop
		else:
			has_resumption_token = False
	
	# Print out the time taken to get all the OAI responses
	# TODO this is for testing
	time_taken = time.time() - start_time
	print "time taken was %f seconds so around %f minutes" % (time_taken, time_taken/60)

	return xml_list

def check_for_res_token(xml_response):
	res_token = ""
	# get the xml root element from response
	root = ET.fromstring(xml_response.content)
		# root[2] is <ListRecords> element - if a resumption token is present it is in a child
		# element of this element, so loop through child elements to look for resumption token
	for child in root[2]:
		# Check if tag contains 'resumptionToken' string
		if 'resumptionToken' in child.tag:
			# If so, assign it's text to token
			res_token = child.text
			break

	return res_token









		
		