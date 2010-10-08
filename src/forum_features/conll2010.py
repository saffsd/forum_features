# Lexical Features
# Not implemented here as we don't provide pos-tagging and lemmatization in this module

# Structural Features
def isThreadInitiator(post):
  return post.author == post.thread.author

def positionRelative(post):
  abs_pos = post.position
  thread_len = len(post.thread)
  return float(abs_pos) / float(thread_len)

# Post context features
# Not implemented here as this has to be done on-the-fly, since it involves the predicted 
# label of the previous post

# Semantic Features
## Title Similarity
from collections import defaultdict
def __token_dist(text):
  count = defaultdict(int)
  for t in text.split():
    count[t] += 1
  return count

def mostSimilarTitleRelative(post):
  position = post.position
  if position == 0: return 0
  this = __token_dist(post.title)
  def similarity(other_post):
    return cosine_similarity(this, __token_dist(other_post.title))
  most_similar = max(post.thread.posts[:position], key=similarity)
  return position - most_similar.position

## Post Similarity
from common import check_tokenized, cosine_similarity
def mostSimilarTextRelative(post):
  check_tokenized(post.thread)
  position = post.position
  if position == 0: return 0
  def similarity(other_post):
    return cosine_similarity(post.token_index, other_post.token_index)
  most_similar = max(post.thread.posts[:position], key=similarity)
  return position - most_similar.position

import re
RE_EXCL = re.compile(r'!')
RE_QUES = re.compile(r'\?')
RE_URL  = re.compile(r'http://')
## Post Characteristics
def questionCount(post):
  return len(RE_EXCL.findall(post.text))
  
def exclamationCount(post):
  return len(RE_QUES.findall(post.text))

def urlCount(post):
  return len(RE_URL.findall(post.text))

## User Profile: Not implemented here as we require information about annotated class priors

structural_features =\
  [ isThreadInitiator
  , positionRelative
  ]

semantic_features =\
  [ mostSimilarTitleRelative
  , mostSimilarTextRelative
  , questionCount
  , exclamationCount
  , urlCount
  ]

from DataModel import rbp_tokenize 
def featdict(post, extractors):
  if post.thread.token_index is None:
    post.thread.forum.run_tokenizer(rbp_tokenize)
  r = {}
  for e in extractors:
    r[e.__name__] = e(post)
  return r

def StructuralFeatures(post): return featdict(post, structural_features)
def SemanticFeatures(post): return featdict(post, semantic_features) 
