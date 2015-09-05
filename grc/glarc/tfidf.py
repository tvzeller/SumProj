# Implementation of TF-IDF
# Some ideas inspired by code at https://code.google.com/p/tfidf/

import re
import operator
import math
from nltk import stem

class Tfidf(object):
	
	def __init__(self):
		self.corpus = []
		self.idf_dict = {}
		self.num_texts = 0

	def add_text(self, text):
		"""
		Adds the given text to the corpus by splitting it and adding each individual word as a key to the idf_dict
		(or incrementing the value if key already present)
		"""
		self.num_texts += 1
		words = re.split("[^\w-]", text.lower())
		word_set = set(words)

		for word in word_set:
			if word in self.idf_dict:
				self.idf_dict[word] += 1
			else:
				self.idf_dict[word] = 1


	def count_words(self, text):
		"""
		Given a text, returns a dict mapping each term in the text to its frequency in the text
		"""
		word_freq = {}
		all_words = re.split("[^\w-]", text.lower())
		word_set = set(all_words)
		for word in word_set:
			word_freq[word] = all_words.count(word)

		return word_freq


	def get_keywords(self, text, maxkw):
		"""
		Given a text and max number, returns the highest scoring words up the max number of words
		"""
		tfidf_scores = {}
		# Get the frequency counts for each word
		word_freq = self.count_words(text)
		# Get the tf-idf score for each word
		for word in word_freq:
			tfidf_scores[word] = word_freq[word] * math.log(self.num_texts / self.idf_dict[word])

		# Sort the words by their tfidf scores into (word, score) tuples
		word_score_pairs = sorted(tfidf_scores.items(), key=operator.itemgetter(1), reverse=True)

		keywords = [word_score[0] for word_score in word_score_pairs]

		return keywords[:maxkw]

	def get_idf_dict(self):
		return self.idf_dict

	def get_num_texts(self):
		return self.num_texts



