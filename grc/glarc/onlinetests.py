	# TODO 
	def test_check_if_in_dept(self):
		author_url = "http://eprints.gla.ac.uk/view/author/9129.html"
		school = "School of Computing Science"
		self.assertTrue(es.check_if_in_dept(author_url, school))