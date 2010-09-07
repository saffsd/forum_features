"""
Implementation of post-level feature extraction
as described by 

Automatic Scoring of Online Discussion Posts, Wanas et. al.
"""

import datetime
import re
from common import check_tokenized, overlap, messenger_emoticons
from itertools import groupby
from DataModel import rbp_tokenize 

def toSeconds(timedelta):
  return timedelta.days * 24 * 60 * 60 + timedelta.seconds
  
## Relevance Features
def onSubForumTopic(post):
  # can't implement OnSubForumTopic - We Don't have a notion of subforum!
  pass

def onThreadTopic(post):
  check_tokenized(post)
  # Leading post is treated specially
  if post == post.thread.posts[0]:
    title_tokens = post.tokenizer(post.thread.title)
    r = overlap(post.token_index, title_tokens)
  else:
    r = overlap(post.token_index, post.thread.posts[0].token_index)
  return r

## Originality Features
def overlapPrevious(post):
  check_tokenized(post)
  overlaps = []
  for p in post.thread.posts:
    if p == post: break
    overlaps.append(overlap(post.token_index, p.token_index))
  return max(overlaps) if overlaps != [] else 0.0

def overlapDistance(post):
  check_tokenized(post)
  overlaps = []
  for i,p in enumerate(post.thread.posts):
    if p == post: break
    overlaps.append(overlap(post.token_index, p.token_index))
  return (i - overlaps.index(max(overlaps))) if overlaps != [] else 0

## Forum-specific Features
# Would need quotation information to extract this, so skipping for now.

## Surface Features
def timeliness(post):
  if post == post.thread.posts[0]: return 0.0
  times = []
  prev = post.thread.posts[0]
  for p in post.thread.posts[1:]:
    times.append(p.date - prev.date)
    prev = p
  mean_time = sum(times, datetime.timedelta()) / len(times)
  t = post.thread
  td = post.date - t.posts[t.posts.index(post) - 1].date
  try:
    r = float(toSeconds(td))/toSeconds(mean_time)
  except ZeroDivisionError:
    # Division by zero indicates that timing data is fubar.
    r = 0.0
  # Set the feature to 0 if we get a negative timeliness.
  # It indicates that the post timing data is not reliable.
  if r < 0.0: r = 0.0
  return r

def lengthiness(post):
  lengths = [ len(p) for p in post.thread.posts ]
  mean_l = sum(lengths) / float(len(lengths))
  r = len(post) / mean_l if mean_l else 0.0
  return r
  
def formatPunctuation(post):
  # Seems to me like this will end up being circular, because we use
  # punctuation to determine sentence boundaries. Therefore this feature
  # should always be 1.0
  pass

def formatEmoticons(post):
  num_emot = sum(1 for e in messenger_emoticons if e in post.text)
  num_sent = len(post.sentences)
  if num_sent == 0: return 0.0
  r = num_emot / float(num_sent)
  return r

def formatCapitals(post):
  cap_chunk_count = 0
  for k, g in groupby(post.text, lambda x: str.isupper(x)):
    if k:
      cap_chunk_count += 1
  num_sent = len(post.sentences)
  if num_sent == 0: return 0.0
  r = cap_chunk_count / float(num_sent)
  return r
  
## Posting Component Features

def weblinks(post):
  link_count = len(re.compile("a href=", re.IGNORECASE).findall(post.text))
  num_sent = len(post.sentences)
  if num_sent == 0: return 0.0
  r = link_count / float(num_sent)
  return r
  

# WeblinkQuality - Not feasible, in terms of bandwidth, and also links
# die over time. 

# Questioning - Not described in much detail

def wanas_Post_features(post):
  # tokenize if not yet done.
  if post.thread.token_index is None:
    post.thread.forum.run_tokenizer(rbp_tokenize)
  features = dict()
  features['onThreadTopic'] = onThreadTopic(post)
  features['overlapPrevious'] = overlapPrevious(post)
  features['overlapDistance'] = overlapDistance(post)
  features['timeliness'] = timeliness(post)
  features['lengthiness'] = lengthiness(post)
  features['formatEmoticons'] = formatEmoticons(post)
  features['formatCapitals'] = formatCapitals(post)
  features['weblinks'] = weblinks(post)
  assert all((v >= 0.0 for v in features.values())), "Ended up with a negative feature!"
  return features

# From wanas testing
  #f.run_tokenizer(rbp_tokenize)
  #for p in f.posts[:100]:
  #  #print p, len(p), onThreadTopic(p), overlapPrevious(p), overlapDistance(p), timeliness(p), lengthiness(p), formatEmoticons(p)
  #  print p, len(p), formatEmoticons(p), formatCapitals(p), weblinks(p)
   
from common import user_post_aggregate
if __name__ == '__main__':
  from DataModel import load_xml, rbp_tokenize
  f = load_xml('adcs.xml')
  #f = load_xml('nabble.xml')
  user_post_aggregate(f, wanas_Post_features)

  import pdb;pdb.set_trace()
