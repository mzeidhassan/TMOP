# sys.path.append(os.getcwd() + '/..') # Uncomment for standalone running
from abstract_filter import *
import os.path
import math
import numpy as np


class LongestUnalignedSequence(AbstractFilter):
	def __init__(self):
		self.var_mult = 2

		self.num_of_scans = 1
		self.src_language = ""
		self.trg_language = ""

		self.n = 0.0

		self.src_sum = 0.0
		self.src_sum_sq = 0.0
		self.trg_sum = 0.0
		self.trg_sum_sq = 0.0

		self.src_mean = 0.0
		self.src_var = 0.0
		self.trg_mean = 0.0
		self.trg_var = 0.0

		self.src_scores = []
		self.trg_scores = []
		self.s_thresh = 0.0
		self.t_thresh = 0.0

		self.model_exist = False

	#
	def initialize(self, source_language, target_language, extra_args):
		self.num_of_scans = 1
		self.src_language = extra_args['source language']
		self.trg_language = extra_args['target language']
		self.normalize = extra_args['normalize scores']
		self.model_filename = "models/LongestUnalignedSequence.stats"
		if self.normalize:
			self.model_filename += "_n"

		if os.path.isfile(self.model_filename):
			lang_pair = self.src_language + self.trg_language
			f = open(self.model_filename, 'r')

			l = f.readline()
			while l:
				if lang_pair not in l:
					l = f.readline()
					continue

				# found the statistics
				self.model_exist = True
				self.num_of_scans = 0

				l = f.readline().strip().split("\t")
				self.src_mean = float(l[1])
				self.src_var = float(l[2])

				l = f.readline().strip().split("\t")
				self.trg_mean = float(l[1])
				self.trg_var = float(l[2])

				break

			f.close()
			if self.model_exist:
				print "Loaded stats from the model file."

		if extra_args['emit scores'] == True:
			self.num_of_scans = 1
		return

	def finalize(self):
		if self.model_exist:
			return

		if self.n <= 1:
			self.n = 2.0
		self.src_mean = self.src_sum / self.n
		self.src_var = (self.src_sum_sq - (self.src_sum * self.src_sum) / self.n) / (self.n - 1)
		self.src_var = math.sqrt(self.src_var)

		self.trg_mean = self.trg_sum / self.n
		self.trg_var = (self.trg_sum_sq - (self.trg_sum * self.trg_sum) / self.n) / (self.n - 1)
		self.trg_var = math.sqrt(self.trg_var)

		f = open(self.model_filename, 'a')
		lang_pair = self.src_language + self.trg_language
		f.write("\n" + lang_pair + "\n")

		f.write("source\t" + str(self.src_mean) + "\t" + str(self.src_var) + "\n")
		f.write("target\t" + str(self.trg_mean) + "\t" + str(self.trg_var) + "\n")

		f.close()

		self.s_thresh = np.percentile(self.src_scores, self.var_mult)
		self.t_thresh = np.percentile(self.trg_scores, self.var_mult)

		f = open("quartiles", "a")

		f.write("LongestUnalignedSequence")
		f.write("\t" + str(np.percentile(self.src_scores, 25)))
		f.write("\t" + str(np.percentile(self.src_scores, 50)))
		f.write("\t" + str(np.percentile(self.src_scores, 75)))

		f.write("\t" + str(np.percentile(self.trg_scores, 25)))
		f.write("\t" + str(np.percentile(self.trg_scores, 50)))
		f.write("\t" + str(np.percentile(self.trg_scores, 75)))
		f.write("\n")

		f.close()

	#
	def process_tu(self, tu, num_of_finished_scans):
		src_set = set([x[0] for x in tu.alignment])
		trg_set = set([x[1] for x in tu.alignment])

		src_size = float(len(tu.src_tokens))
		trg_size = float(len(tu.trg_tokens))

		if src_size == 0 or trg_size == 0:
			return [0.0, 0.0]

		self.n += 1
		max_src_seqs = 0.0
		last = -1
		for current in src_set:
			if current - last > 1:
				max_src_seqs = max(max_src_seqs, current - last - 1)
			last = current
		if src_size - last > 1:
			max_src_seqs = max(max_src_seqs, src_size - last - 1)
		max_src_seqs /= src_size

		max_trg_seqs = 0.0
		last = -1
		for current in trg_set:
			if current - last > 1:
				max_trg_seqs = max(max_trg_seqs, current - last - 1)
			last = current
		if trg_size - last > 1:
			max_trg_seqs = max(max_trg_seqs, trg_size - last - 1)
		max_trg_seqs /= trg_size

		if self.normalize:
			max_src_seqs = 1.0 - min(max_src_seqs, 1.0)
			max_trg_seqs = 1.0 - min(max_trg_seqs, 1.0)

		self.src_sum += max_src_seqs
		self.src_sum_sq += max_src_seqs * max_src_seqs
		self.trg_sum += max_trg_seqs
		self.trg_sum_sq += max_trg_seqs * max_trg_seqs

		self.src_scores.append(max_src_seqs)
		self.trg_scores.append(max_trg_seqs)

		return [max_src_seqs, max_trg_seqs]

	#
	def do_after_a_full_scan(self, num_of_finished_scans):
		pass

	def decide(self, tu):
		src_set = set([x[0] for x in tu.alignment])
		trg_set = set([x[1] for x in tu.alignment])
		src_size = float(len(tu.src_tokens))
		trg_size = float(len(tu.trg_tokens))

		if src_size == 0 or trg_size == 0:
			return 'reject'

		max_src_seqs = 0.0
		last = -1
		for current in src_set:
			if current - last > 1:
				max_src_seqs = max(max_src_seqs, current - last - 1)
			last = current
		if src_size - last > 1:
			max_src_seqs = max(max_src_seqs, src_size - last - 1)
		max_src_seqs /= src_size

		max_trg_seqs = 0.0
		last = -1
		for current in trg_set:
			if current - last > 1:
				max_trg_seqs = max(max_trg_seqs, current - last - 1)
			last = current
		if trg_size - last > 1:
			max_trg_seqs = max(max_trg_seqs, trg_size - last - 1)
		max_trg_seqs /= trg_size

		if self.normalize:
			max_src_seqs = 1.0 - min(max_src_seqs, 1.0)
			max_trg_seqs = 1.0 - min(max_trg_seqs, 1.0)

		max_src_seqs = abs(max_src_seqs - self.src_mean)
		max_trg_seqs = abs(max_trg_seqs - self.trg_mean)

		if max_src_seqs > self.var_mult * self.src_var or max_trg_seqs > self.var_mult * self.trg_var:
		# if max_src_seqs < self.s_thresh or max_trg_seqs < self.t_thresh:
			return 'reject'
		return 'accept'
