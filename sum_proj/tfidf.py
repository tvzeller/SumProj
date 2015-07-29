# TODO refactoring needed

# Implementation of TF-IDF

import re
import operator

class Extractor(object):
	
	def __init__(self):
		self.corpus = []
		self.idf_dict = {}
		self.num_texts = 0

	def add_text(self, text):
		self.num_texts += 1
		words = re.split("[^\w-]", text.lower())
		word_set = set(words)
		for word in word_set:
			if word in self.idf_dict:
				self.idf_dict[word] += 1
			else:
				self.idf_dict[word] = 1

	def count_words(self, text):
		word_freq = {}
		all_words = re.split("[^\w-]", text.lower())
		word_set = set(all_words)
		for word in word_set:
			word_freq[word] = all_words.count(word)

		return word_freq

	def sort_by_count(self, word_count_dict):
		pass


	def get_keywords(self, text):
		tfidf_scores = {}
		word_freq = self.count_words(text)
		for word in word_freq:
			tfidf_scores[word] = word_freq[word] * (self.num_texts / self.idf_dict[word])

		word_score_pairs = sorted(tfidf_scores.items(), key=operator.itemgetter(1), reverse=True)
		keywords = [word_score[0] for word_score in word_score_pairs]
		return keywords[:5]



