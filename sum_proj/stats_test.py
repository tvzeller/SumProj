import unittest
import cvg_stats as cs
# TODO this is in the same directory as other modules for now until I figure out
# how to import from a different directory

# TODO add more tests?...

class GoodDictTestCase(unittest.TestCase):
	def setUp(self):
		my_dict = {
			"Albert Einstein": (["paper1", "paper2", "paper3", "paper4"], ["paper2", "paper3"]),
			"Donald Knuth": (["paper1", "paper2", "paper3", "paper4", "paper5"], ["paper1", "paper4"]),
			"Bob Dylan": (["paper1"], ["paper1"])
		}
		self.stats = cs.Stats(my_dict)

	def test_cvg_dict(self):
		expected_dict = {
			"Albert Einstein": 0.5,
			"Donald Knuth": 0.4,
			"Bob Dylan": 1.0
		}
		self.assertEqual(self.stats.get_cvg_dict(), expected_dict)

	def test_mean_cvg(self):
		self.assertEqual(self.stats.get_mean_cvg(), 63.33)

	def test_author_cvg(self):
		self.assertEqual(self.stats.get_author_cvg("Albert Einstein"), 0.5)

	def test_invalid_author(self):
		self.assertIsNone(self.stats.get_author_cvg("Albert Heinstein"))

	def test_get_range(self):
		expected = {'max': 1.0, 'min': 0.4}
		self.assertEqual(self.stats.get_range(), expected)


	# def test_no_titles(self):
	# 	my_dict = {"Albert Einstein": ([], [])}
	# 	stats = cs.Stats(my_dict)
	# 	expected_dict = {"Albert Einstein": 0.0}
	# 	self.assertEqual(stats.get_cvg_dict(), expected_dict)


class EmptyDictTestCase(unittest.TestCase):
	def setUp(self):
		self.stats = cs.Stats({})

	def test_cvg_dict(self):
		self.assertEqual(self.stats.get_cvg_dict(), {})

	def test_mean_cvg(self):
		self.assertEqual(self.stats.get_mean_cvg(), 0.0)

	def test_get_range(self):
		expected = {'max': 0.0, 'min': 0.0}
		self.assertEqual(self.stats.get_range(), expected)

	def test_author_cvg(self):
		self.assertIsNone(self.stats.get_author_cvg("Albert Einstein"))

	def test_total_cvg(self):
		self.assertEquals(self.stats.get_total_cvg(), 0.0)


class DivideByZeroTestCase(unittest.TestCase):
	def setUp(self):
		my_dict = {"Albert Einstein": ([], [])}
		self.stats = cs.Stats(my_dict)

	def test_cvg_dict(self):
		expected_dict = {"Albert Einstein": 0.0}
		self.assertEqual(self.stats.get_cvg_dict(), expected_dict)

	
class WrongTypeTestCase(unittest.TestCase):
	def setUp(self):
		self.stats = cs.Stats("Not a dict")

	def test_cvg_dict(self):
		self.assertEquals(self.stats.get_cvg_dict(), {})

	def test_mean_cvg(self):
		self.assertEquals(self.stats.get_mean_cvg(), 0.0)

	def test_get_range(self):
		expected = {'max': 0.0, 'min': 0.0}
		self.assertEqual(self.stats.get_range(), expected)

	def test_author_cvg(self):
		self.assertIsNone(self.stats.get_author_cvg("Albert Einstein"))

	def test_total_cvg(self):
		self.assertEquals(self.stats.get_total_cvg(), 0.0)



if __name__ == '__main__':
	unittest.main()
