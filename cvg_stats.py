# Consider having coverage dict as an instance variable (built with constructor)
# so don't have to recalculate every time
# but think about encapsulation

# Note also - this is a class because several functions use the title_dict, which
# is an instance variable - this is the justification

class Stats(object):
	def __init__(self, td, sbj):
		self.title_dict = td 
		self.subject = sbj

	
	def get_cvg_dict(self):
		cvg_dict = {}
		for author in self.title_dict:
			all_titles = self.title_dict[author][0]
			tagged_titles = self.title_dict[author][1]
			pct_cvg = (len(tagged_titles) * 1.0) / len(all_titles)
			cvg_dict[author] = pct_cvg
		return cvg_dict


	def get_mean_cvg(self):
		# TODO what if cvg_dict is empty? i.e. no authors - here would be dividing by 0
		# fix this and other such potential edge cases
		cvg_dict = self.get_cvg_dict()
		mean = (sum(cvg_dict.values()) / len(cvg_dict)) * 100
		return mean


	def get_range(self):
		cvg_dict = self.get_cvg_dict()
		max_cvg = max(cvg_dict.values())
		min_cvg = min(cvg_dict.values())
		return {'max': max_cvg, 'min': min_cvg}

	def get_author_cvg(self, name):
		all_titles = self.title_dict[name][0]
		tagged_titles = self.title_dict[name][1]
		cvg = (len(tagged_titles) * 1.0) / len(all_titles)
		return cvg

	def get_total_cvg(self):
		total_count = 0
		tagged_count = 0
		for total, tagged in self.title_dict.values():
			total_count += len(total)
			tagged_count += len(tagged)
		total_cvg = tagged_count * 1.0 / total_count
		return total_cvg

	def write_to_file(self, filename):
		mean = self.get_mean_cvg()
		range_dict = self.get_range()
		tot_cvg = self.get_total_cvg()
		s = "%s\nMean author coverage: %f\nMax: %f\nMin: %f\nTotal Coverage: %f\n\n" % (self.subject, mean, range_dict['max'], range_dict['min'], tot_cvg)
		with open(filename, 'a') as f:
			f.write(s)
