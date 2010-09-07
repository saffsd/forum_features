import math
from HTMLParser import HTMLParser, HTMLParseError
from htmlentitydefs import entitydefs

class CleanPost(HTMLParser):
  # TODO: Don't swallow images
  def reset(self):
    HTMLParser.reset(self)
    self.text = ''

  def __call__(self,data):
    self.reset()
    for l in data.split('\n'):
      l = l.strip()
      if l != '<br />':
        try:
          self.feed(l)
          self.text += '\n'
        except HTMLParseError:
          self.text += l + '\n'
    return self.text
        
  def handle_data(self, data):
    self.text += data 

  def handle_entityref(self, name):
    try:
      self.text += entitydefs[name]
    except KeyError:
      self.text += '<ENTITY>'

  def handle_starttag(self, tag, attrs):
    if tag == 'img':
      self.text += '<IMAGE>'
    

def check_tokenized(e):
  if e.token_index is None:
    raise ValueError, "Please run tokenizer first"

messenger_emoticons =\
  [ ':)'  , ':D'  , ';)'  , ':-O'  , ':P'  , '(H)'  , ':('  , ":'("  , ":|"  , "(brb)"
  , ":$"  , ":S"  , ":^)"  , "*-)"  , "*-)"  , "|-)"  , ":-#"  , "*o|"  , "<:o)"
  , "+o("  , ":@"  , "(6)"  , "(A)"  , "8-|"  , "^o)"  , ":-*"  , "(Y)"  , "(N)"
  , "(h5)"  , "(yn)"  , "({)"  , "({)"  , "(Z)"  , "(X)"  , "(M)"  , "(L)"  , "(U)"
  , "(F)"  , "(W)"  , "(K)"  , "(G)"  , "(^)"  , "<:o)"  , "(ci)"  , "(%)"  , "(B)"
  , "(D)"  , "(S)"  , "(*)"  , "(#)"  , "(R)"  , "(um)"  , "(ip)"  , "(st)"  , "(li)"
  , "(pl)"  , "(ll)"  , "(pi)"  , "(^)"  , "(C)"  , "(@)"  , "(&)"  , ":["  , "(nah)"
  , "(sn)"  , "(tu)"  , "(bah)"  , "(~)"  , "(8)"  , "(E)"  , "(P)"  , "(I)"  , "(O)"
  , "(T)"  , "(co)"  , "(mp)"  , "(xx)"  , "(so)"  , "(au)"  , "(ap)"  , "(mo)"
  ]

# Similarity Metrics for feature dictionaries 
def overlap(child, parent):
  """
  Overlap as defined by wanas et al
  """
  common = 0
  for k in child:
    if k in parent:
      common += child[k]
  total = sum(child.values())
  if total == 0:
    return 0.0
  else:
    return float(common) / total

def cosine_similarity(d1, d2):
  """
  The vector space model stalwart, Cosine Similarity
  """
  w = math.sqrt(sum(t * t for t in d1.values())) * math.sqrt(sum(t * t for t in d2.values()))
  if w == 0.0:
    return 0
  
  acc = 0.0
  for t in d1:
    if t in d2:
      acc += d1[t] + d2[t]
  return acc / w
      
def mean(seq):
  seq = list(seq)
  return sum(seq) / float(len(seq))

import numpy
def feature_mean(featurelist):
  all_keys = reduce(set.union,featurelist, set())
  agg = {}
  for key in all_keys:
    agg[key] = mean(f[key] for f in featurelist if key in f)
  return agg

class ThreadSingleuserFeatures:
  """
  Extract thread features based on selecting a specific role in
  the thread
  """
  def __init__(self, user_selector, user_feat_extractor):
    self.user_selector = user_selector
    self.user_feat_extractor = user_feat_extractor

  def __call__(self, thread):
    f = thread.forum
    user = self.user_selector(thread)
    if user is not None:
      fv = self.user_feat_extractor(user)
    else:
      fv = {}
    return fv

class UserPostAggregate:
  """
  Extract user features based on aggregating post-level features
  """
  def __init__(self, feature_extractor, aggregator):
    self.feature_extractor = feature_extractor
    self.aggregator = aggregator

  def __call__(self, user):
    f = [ self.feature_extractor(p) for p in user.posts ]
    fv = self.aggregator(f)
    return fv

def user_post_aggregate(forum, feature_extractor, aggregator=feature_mean, users=None):
  if users is None: users = [ a for a in forum.authors ]
  features = {}
  for user in users:
    A = forum.authors[user]
    f = [ feature_extractor(p) for p in A.posts ]
    features[user] = aggregator(f)
  return features

class ThreadPostFeatures:
  def __init__(self, feature_extractor, aggregator=None):
    if aggregator is None:
      self.aggregator = feature_mean
    else:
      self.aggregator = aggregator
    self.feature_extractor = feature_extractor

  def __call__(self, thread):
    f = [ self.feature_extractor(p) for p in thread.posts ]
    feats = self.aggregator(f)
    return feats

