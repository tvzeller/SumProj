# TODO refactoring needed

# Implementation of TF-IDF

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
		self.num_texts += 1
		words = re.split("[^\w-]", text.lower())
		#words = self.stem_words(words)
		word_set = set(words)
		for word in word_set:
			if word in self.idf_dict:
				self.idf_dict[word] += 1
			else:
				self.idf_dict[word] = 1

	def stem_words(self, words):
	# WAIT should the keywords in author keywords be stemmed???
	# Yes - gives better chance of finding a match... More recall, less precision
		# TODO initialise these somewhere else
		prtr = stem.porter.PorterStemmer()
		#wnl = WordNetLemmatizer()
		# So as not to change original list... to be discussed
		words_copy = words[:]
		for index, word in enumerate(words_copy):
			# Use a better split here
			tokens = word.split()
			#stemmed_phrase = ""
			stemmed_token = ""
			for token in tokens:
				stemmed_token = prtr.stem(token).lower()
				#stemmed_phrase += stemmed_token + " "

			if stemmed_token:
				words[index] = stemmed_token.strip()

		return words

	def count_words(self, text):
		word_freq = {}
		all_words = re.split("[^\w-]", text.lower())
		#all_words = self.stem_words(all_words)
		word_set = set(all_words)
		for word in word_set:
			word_freq[word] = all_words.count(word)

		return word_freq

	def sort_by_count(self, word_count_dict):
		pass


	def get_keywords(self, text, maxkw):
		tfidf_scores = {}
		word_freq = self.count_words(text)
		for word in word_freq:
			tfidf_scores[word] = word_freq[word] * math.log(self.num_texts / self.idf_dict[word])

		word_score_pairs = sorted(tfidf_scores.items(), key=operator.itemgetter(1), reverse=True)
		word_score_pairs = [(wsp[0], wsp[1]*100) for wsp in word_score_pairs]
		#keywords = [word_score[0] for word_score in word_score_pairs]
		# TODO
		return word_score_pairs[:maxkw]

	def get_idf_dict(self):
		return self.idf_dict

	def get_num_texts(self):
		return self.num_texts



