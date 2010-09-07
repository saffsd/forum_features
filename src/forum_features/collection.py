"""
Collection-level user features
"""
from itertools import groupby
from operator import attrgetter
from collections import defaultdict
from DataModel import PostList

def partition_by_author(thread):
  return [(a, PostList(posts)) for a,posts in groupby(thread, attrgetter('author'))]
  
def initiator(thread):
  return thread.forum.authors[partition_by_author(thread)[0][0]]

def first_responder(thread):
  try:
    return thread.forum.authors[partition_by_author(thread)[1][0]]
  except IndexError:
    return None

def final_responder(thread):
  try:
    return thread.forum.authors[partition_by_author(thread)[-1][0]]
  except IndexError:
    return None

def rel_distribution(seq):
  assert len(seq) > 0
  d = defaultdict(int)
  for s in seq:
    d[s] += 1
  total = float(sum(d.values()))
  output = dict((k, d[k] / total) for k in d)
  return output


from forum_features.DataModel import load_xml
if __name__ == "__main__":
  dataP = '/home/mlui/.virtualenvs/iliad/data/cnet.xml'
  f = load_xml(dataP)
  r = rel_distribution( map(first_responder, f.threads) )
  import pdb;pdb.set_trace()
