
import numpy as np
import json
import sys
import os
import sklearn.svm

import pymongo

import itertools

from QueryEngineCore import QueryEngineCore
from DocVectorizer import Word2vecDocVectorizer, TfIdfDocVectorizer


data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'largedata');

class VectorizerDocSearchEngine:
	def __init__(self):
		# We expect a MongoDB instance to be running. It should have
		# database 'sharesci', where token2id and id2freq are stored in
		# a 'special_objects' collection and documents are from the
		# 'cranfield' collection.
		mongo_client = pymongo.MongoClient('localhost', 27017)
		self._mongo_db = mongo_client['sharesci']

		token2id = self._mongo_db['special_objects'].find_one({'key': 'token2id'})['value']
		self._id2freq = self._mongo_db['special_objects'].find_one({'key': 'id2freq'})['value']

		docs = []
		self._idx2id = []
		self._id2idx = dict()
		for mongo_doc in self._mongo_db['papers'].find({}):
			# ID is mapped to the current index in the `docs` array
			# Obviously, it's important to do this before appending
			# to `docs`.
			self._id2idx[str(mongo_doc['_id'])] = len(docs)

			# Map the current doc's index in the array to its ID
			self._idx2id.append(str(mongo_doc['_id']))

			docs.append(mongo_doc['body'])


		self._vectorizer = Word2vecDocVectorizer(token2id, os.path.join(data_dir, 'word2vec_vectors.npy'))

		self._doc_embeds = self._vectorizer.make_doc_embedding_storage(docs)
		self._query_engine = QueryEngineCore(self._doc_embeds, comparator_func=np.dot)


	def search_qs(self, query, **generic_search_kwargs):
		query_vec = self._vectorizer.make_doc_vector(query);
		query_unitvec = query_vec/np.linalg.norm(query_vec)

		return self.search_queryvec(query_unitvec, **generic_search_kwargs)


	def search_docid(self, doc_id, **generic_search_kwargs):
		query_vec = self._doc_embeds.get_by_id(self._id2idx[doc_id]);
		return self.search_queryvec(query_vec, **generic_search_kwargs)


	def search_userid(self, user_id, max_results=sys.maxsize, offset=0, getFullDocs=False):
		if max_results == 0:
			max_results = sys.maxsize

		# Init the history vector for the user
		user_history_vec = np.zeros(len(self._doc_embeds))

		# Get user history
		cursor = self._mongo_db['users'].find({'_id': user_id}, {'_id': 1, 'docIds': 1}).limit(1)
		if cursor.count() == 0:
			return []

		# Convert user history to vector
		# Note: we make and store the array for doc indexes to use them
		# again later
		user_docIds_arr = cursor[0]['docIds']
		user_docIdxs = set()
		for docId in user_docIds_arr:
			if docId not in self._id2idx:
				continue
			user_docIdxs.add(self._id2idx[docId])
		for docIdx in user_docIdxs:
			user_history_vec[docIdx] = 1

		# If there weren't any example docs, the SVM can't train, so
		# just fail and return empty
		if len(user_docIdxs) == 0:
			return []

		# Train the SVM
		# TODO: Move this process offline so we don't have to train from scratch on every query
		user_svm = sklearn.svm.LinearSVC(class_weight='balanced', verbose=False, max_iter = 2000, C=0.1, tol=1e-5)
		user_svm.fit(self._doc_embeds.as_numpy_array(), user_history_vec)

		results = QueryEngineCore.search_static(np.zeros(1), self._doc_embeds, lambda vec, qvec: float(user_svm.decision_function([vec])), max_results=(offset+max_results+len(user_docIds_arr)))

		# Filter to exclude any docs the user has already seen
		results[:] = itertools.filterfalse((lambda x: x[1] in user_docIdxs), results)

		# Get the specified result window
		results = results[offset:offset+max_results]

		return self._convert_result_format(results)
		

	def search_queryvec(self, query_vec, max_results=sys.maxsize, offset=0, getFullDocs=False):
		if max_results == 0:
			max_results = sys.maxsize

		results = self._query_engine.search(query_vec, max_results=(offset+max_results))[offset:(offset+max_results)]

		return self._convert_result_format(results)


	def _convert_result_format(self, search_results):

		# Convert doc IDs
		converted_results = []
		for result in search_results:
			if result[0] < 0:
				continue
			res_aslist = list(result)
			res_aslist[1] = self._idx2id[result[1]]
			converted_results.append(tuple(res_aslist))

		return converted_results
		

