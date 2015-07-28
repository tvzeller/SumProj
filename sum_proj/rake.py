# TODO refactoring needed

# Rapid Automatic Keyword Extraction from "Automatic keyword extraction for individual documents" in "Text Mining: Applications and Theory"
# -*- coding: utf-8 -*-
import re
import operator

class Rake(object):

	def __init__(self):
		self.stopwords = set()
		#self.keyphrases
		self.ind_word_scores = {}


	def add_stopwords(self, stopwordsfile):
		with open(stopwordsfile) as f:
			for line in f:
				self.stopwords.add(line.strip())


	def get_keyphrases(self, text):
		words = re.split("\s", text.lower())
		keyphrases = []
		index = 0
		last_word_was_stopword = True

		for word in words:
			if word.strip() in self.stopwords:
				if not last_word_was_stopword:
					index += 1
					last_word_was_stopword = True
			else:
				last_word_was_stopword = False
				if len(keyphrases) > index:
					keyphrases[index] += " " + word.strip()
				else:
					keyphrases.append(word.strip())

		#keywords2 = []
		#for kw in keywords:
		keyphrases = [word.strip() for kp in keyphrases for word in re.split("[^-\w ]", kp)]
		print keyphrases
		return keyphrases

	def calc_ind_word_scores(self, kp):

		word_freq = {}
		word_deg = {}

		for phrase in kp:
			ind_words = phrase.split()
			deg = len(ind_words)
			for word in ind_words:
				if word in word_freq:
					word_freq[word] += 1
					word_deg[word] += deg
				else:
					word_freq[word] = 1
					word_deg[word] = deg

		# TODO Final score can be either frequency, degree or degree/frequency
		for word in word_freq:
			self.ind_word_scores[word] = (word_deg[word] * 1.0) / word_freq[word]
			#self.ind_word_scores[word] = word_freq[word]

		sorted_word_scores = sorted(self.ind_word_scores.items(), key=operator.itemgetter(1), reverse=True)

	
	def calc_keyphrase_scores(self, word_scores, kp):
		keyphrase_scores = {}
		for phrase in kp:
			keyphrase_scores[phrase] = 0
			ind_words = phrase.split()
			for word in ind_words:
				keyphrase_scores[phrase] += self.ind_word_scores[word]

		sorted_kp_scores = sorted(keyphrase_scores.items(), key=operator.itemgetter(1), reverse=True)
		print sorted_kp_scores
		return sorted_kp_scores


if __name__ == "__main__":
	r = Rake()
	r.add_stopwords("stopwords.txt")
	kp = r.get_keyphrases("""Compatibility of systems of linear constraints over the set of natural numbers 
							Criteria of compatibility of a system of linear Diophantine equations, strict inequations, 
							and nonstrict inequations are considered. Upper bounds for components of a minimal set 
							of solutions and algorithms of construction of minimal generating sets of solutions for all
							types of systems are given. These criteria and the corresponding algorithms for 
							constructing a minimal supporting set of solutions can be used in solving all the
							considered types of systems and systems of mixed types.""")
	ws = r.calc_ind_word_scores(kp)
	kp_scores = r.calc_keyphrase_scores(ws, kp)
	print kp_scores




		


