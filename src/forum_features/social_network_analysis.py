import networkx as nx
from collections import defaultdict
from common import cosine_similarity
import shelve
import uuid
import logging

# Implementing feature generation methods from Fortuna, Rodrigues and Milic-Frayling

#####
# Network Cache
#####
class NetworkCache:
  """
  Quick implementation of a persistency solution for networks, using the
  python shelve module. Shelve mysteriously demands that all keys be
  ints or strs, so we get around this by keeping our own index of the
  keys in a standard dict, which maps from a full key to a uuid-generated
  shelve key. We keep the index in memory, and persist it in the shelf
  under the key 'index'. We rewrite the whole index each time it is 
  updated - there's no simple way for a partial update.
  Networks must be calculated via computenetwork in order for output
  to be cached. This also makes the assumption that the forum data is
  static (we only use the forum name as an identifier!), and that the
  functions are deterministic. The key used for caching is as follows:
    key = (net_fn.__name__, forum.title, frozenset(kwargs.items()))
  """
  def __init__(self, path, flag='c'):
    self.logger = logging.getLogger('social_network_analysis')
    self.cache = shelve.open(path, flag=flag, protocol=-1) 
    if 'index' in self.cache:
      self.index = self.cache['index']
    else:
      self.index = {}

  def update(self, other):
    for key in other:
      self[key] = other[key]

  def __iter__(self):
    return iter(self.index)

  def __contains__(self, key):
    return key in self.index

  def __getitem__(self, key):
    real_key = self.index[key]
    return self.cache[real_key]
    
  def __setitem__(self, key, value):
    if key in self.index:
      real_key = self.index[key]
    else:
      real_key = str(uuid.uuid4())
      self.index[key] = real_key
    self.cache[real_key] = value
    self.cache['index'] = self.index

  def __delitem__(self, key):
    real_key = self.index[key]
    try:
      del self.cache[real_key]
    except:
      pass
    del self.index[key]
    self.cache['index'] = self.index

  def compute_network(self, net_fn, forum, **kwargs):
    key = (net_fn.__name__, forum.title, frozenset(kwargs.items()))
    self.logger.info("Retrieving network for %s", str(key))
    if key in self:
      try:
        net = self[key]
        return net
      except Exception, e:
        self.logger.warning("Failed with error: %s", str(e))
        del self[key]
    self.logger.info("Computing network for %s", str(key))
    net = net_fn(forum, **kwargs)
    self[key] = net
    return net

    
  def __del__(self):
    self.cache['index'] = self.index
    self.cache.close()

##########
# Social Network Mixin
##########
    
class SocialNetwork(object):
  def __init__(self, edge_fn):
    self.edge_fn = edge_fn

  def __repr__(self):
    return '<%s with %d nodes, %d edges>' % (self.__class__.__name__, len(self.nodes()), len(self.edges()))

  def __str__(self):
    return repr(self)

  def feature_vector(self, A):
    fv = defaultdict(int)
    for B in self.nodes():
      if self.edge_fn(A, B):
        # Adjacency scores 1
        fv[B.id] = 1.0
        for neigh in self.neighbors_iter(B):
          if neigh.id not in fv:
            # Second-order adjacency scores 0.5
            fv[neigh.id] = 0.5
    return fv

##########
# Abstract Author Networks
##########
class AuthorNetwork(SocialNetwork, nx.Graph):
  """
  Represents social networks with authors as the individual
  nodes, where the edges are undirected. For example, thread co-participation.
  """
  def __init__(self, edge_fn):
    SocialNetwork.__init__(self, edge_fn)
    nx.Graph.__init__(self)
    
  def __call__(self, forum):
    authors = [forum.authors[a] for a in sorted(forum.authors)]
    for i,A in enumerate(authors):
      for B in authors[i:]:
        if A != B and self.edge_fn(A, B):
          self.add_edge(A,B)

  def feature_vector(self, A):
    fv = defaultdict(int)
    for B in self.nodes():
      if self.edge_fn(A, B):
        # Adjacency scores 1
        fv[B.name] = 1.0
        for neigh in self.neighbors_iter(B):
          if neigh.name not in fv:
            # Second-order adjacency scores 0.5
            fv[neigh.name] = 0.5
    return fv

class DirectedAuthorNetwork(SocialNetwork, nx.DiGraph):
  """
  Represents social networks with authors as the individual
  nodes, where the edges are directed. For example, a reply-to graph.
  """
  def __init__(self, edge_fn):
    SocialNetwork.__init__(self, edge_fn)
    nx.DiGraph.__init__(self)
    
  def __call__(self, forum):
    authors = [forum.authors[a] for a in sorted(forum.authors)]
    for i,A in enumerate(authors):
      for B in authors[i:]:
        if A != B:
          # Need to test both directions for a directed graph.
          if self.edge_fn(A,B):
            self.add_edge(A,B)
          if self.edge_fn(B,A):
            self.add_edge(B,A)

  def feature_vector(self, A):
    fv = defaultdict(int)
    for B in self.nodes():
      if self.edge_fn(A, B):
        # Adjacency scores 1
        fv[B.name] = 1.0
        for neigh in self.neighbors_iter(B):
          if neigh.name not in fv:
            # Second-order adjacency scores 0.5
            fv[neigh.name] = 0.5
    return fv

#####
# Thread Networks 
# May need a directed thread network?
#####
class ThreadNetwork(SocialNetwork, nx.Graph):
  def __init__(self, edge_fn):
    nx.Graph.__init__(self)
    self.edge_fn = edge_fn

  def __call__(self, forum):
    for i,T in enumerate(forum.threads):
      for Q in forum.threads[i:]:
        if T != Q and self.edge_fn(T, Q):
          #print "Edge from", repr(T), "to", repr(Q) 
          self.add_edge(T,Q)

  def feature_vector(self, A):
    """
    A is a thread
    """
    fv = defaultdict(int)
    for B in self.nodes():
      if self.edge_fn(A, B):
        # Adjacency scores 1
        fv[B.id] = 1.0
        for neigh in self.neighbors_iter(B):
          if neigh.id not in fv:
            # Second-order adjacency scores 0.5
            fv[neigh.id] = 0.5
    return fv

##########
# Edge Functions
##########

class EdgeFunction(object):
  def __call__(self, T, Q):
    return self.hasEdge(T,Q)

#####
# Thread Network Edge Functions
#####
class CommonAuthor(EdgeFunction):
  def __init__(self, m):
    self.m = m

  def hasEdge(self, T, Q):
    return len(T.post_authors & Q.post_authors) >= self.m
    
class TextSimilarity(EdgeFunction):
  def __init__(self, n, sim_fn):
    self.n = n
    self.sim_fn = sim_fn

  def hasEdge(self, T, Q):
    try:
      similarity = self.sim_fn(T.token_index, Q.token_index) 
      #if similarity >= self.n: print similarity
      return similarity >= self.n
    except AttributeError:
      raise ValueError, "No token indexes!"

#####
# Author Network Edge Functions
#####
class PostAfter(EdgeFunction):
  """
  Edge exists if author B has posted within dist posts of author
  A on at least count occasions. The occasions can all occur in 
  the same thread
  """
  def __init__(self, dist, count):
    self.dist = dist
    self.count = count

  def hasEdge(self, A, B):
    count = 0
    for p in B.posts:
      curr_post = p
      for i in range(self.dist):
        curr_post = curr_post.next_by_thread()
        # No more posts in the thread to consider
        if curr_post is None: break
        if curr_post.author == A.name: count += 1
    return count >= self.count
    
# Conversation network? A - B - A - B pattern?

class ThreadParticipation(EdgeFunction):
  def __init__(self, k):
    self.k = k

  def hasEdge(self, A, B):
    # Ensure A is the one with less threads for computational efficiency
    if len(A.all_threads) > len(B.all_threads): A,B = B,A
    count = sum(1 for T in A.all_threads if B in T)
    return count >= self.k

##########
# Concrete networks
#########
def CommonAuthorsNetwork(forum, m = 3):
  g = ThreadNetwork(CommonAuthor(m))
  g(forum)
  return g

def TextSimilarityNetwork(forum, n=0.3):
  g = ThreadNetwork(TextSimilarity(n, cosine_similarity))
  g(forum)
  return g

def PostAfterNetwork(forum, dist=1, count=3):
  g = DirectedAuthorNetwork(PostAfter(dist=dist, count=count))
  g(forum)
  return g

def ThreadParticipationNetwork(forum, k=5):
  g = AuthorNetwork(ThreadParticipation(k))
  g(forum)
  return g

########
# Analysis
########

if __name__ == '__main__':
  from DataModel import load_xml, rbp_tokenize
  #f = load_xml('adcs.xml')
  f = load_xml('nabble.xml')
  #f.run_tokenizer(rbp_tokenize)
  g = ThreadParticipationNetwork(f, k=1)
  import pdb;pdb.set_trace()
