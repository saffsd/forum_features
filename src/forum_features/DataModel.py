import string
import datetime as dt
import time
from collections import defaultdict
from cStringIO import StringIO
import xml.etree.cElementTree as etree
from cStringIO import StringIO
import random
from xml.sax.saxutils import escape, unescape

# From http://stackoverflow.com/questions/92438/stripping-non-printable-characters-from-a-string-in-python
import unicodedata, re
all_chars = (unichr(i) for i in xrange(0x110000))
control_chars = ''.join(map(unichr, range(0,10)+range(11,32)+range(127,160)))
control_char_re = re.compile('[%s]' % re.escape(control_chars))

def clean(s):
    return control_char_re.sub('', s)

def load_xml(file):
  tree = etree.parse(file)
  title = tree.find('title').text
  forum = Forum(title)
  for t_node in tree.findall('thread'):
    thread_id = t_node.get('id')
    title = unescape(t_node.find('title').text or '')
    author = unescape(t_node.find('author').text or '')
    date = float(t_node.find('date').text)
    forum.add_Thread(thread_id, title, author, date)
    for p_node in t_node.findall('post'):
      post_id = p_node.get('id')
      title = unescape(p_node.find('title').text or '')
      author = unescape(p_node.find('author').text or '')
      date = float(p_node.find('date').text)
      t = p_node.find('text').text
      # Undo the cleverness from etree in detecting and returning
      # utf8 nodes.
      #if type(author) == unicode:    author = author.encode('utf8')
      #if type(title) == unicode:     title = title.encode('utf8')
      if type(t) == unicode:         t = t.encode('utf8')
      text = unescape(t if t is not None else '')
      forum.add_Post(thread_id, post_id, title, author, date, text)
  return forum 

class Forum(object):
  def __init__(self, title):
    self.title = title
    self.threads = [] 
    self.thread_dict = {}
    self.posts = []
    self.post_dict = {}
    self.authors = defaultdict(Author) 
    self.token_index = None
    self.tokenizer = None


  def __eq__(self, other):
    return self.threads == other.threads

  def __getitem__(self, key):
    return self.thread_dict[key]

  def __repr__(self):
    return "<forum %s, %d threads, %d posts, %d authors>" % ( self.title
                                                            , len(self.threads)
                                                            , len(self.posts)
                                                            , len(self.authors)
                                                            )

  @property
  def xml(self):
    b = etree.TreeBuilder()

    b.start('forum',{})

    b.start('title',{})
    b.data(self.title)
    b.end('title')

    b.end('forum')
    e = b.close()

    for t in self.threads:
      e.append(t.xml)

    return e

  def sample(self, k, seed=None):
    assert k <= len(self.threads), "Not enough threads to sample"
    random.seed(seed)
    subforum = Forum(self.title+'_(k:%d,seed:%s)'%(k,str(seed)))
    for thread in random.sample(self.threads, k):
      subforum.add_Thread(thread.id, thread.title, thread.author, time.mktime(thread.date.timetuple()))
      for post in thread.posts:
        subforum.add_Post(thread.id, post.id, post.title, post.author, time.mktime(post.date.timetuple()), post.text)
    return subforum


  def writexml(self, writer):
    # from http://effbot.org/zone/element-lib.htm#prettyprint
    def indent(elem, level=0):
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i
    e = self.xml
    indent(e)
    tree = etree.ElementTree(e)
    tree.write(writer)
  
  def add_Thread(self, thread_id, title, author, date):
    thread = Thread(thread_id, clean(title), clean(author), date, self)
    self.threads.append(thread)
    self.thread_dict[thread_id] = thread
    self.authors[author].add_Thread(thread)

  def add_Post(self, thread_id, post_id, title, author, date, text):
    thread = self.thread_dict[thread_id]
    post = thread.add_Post(post_id, clean(title), clean(author), date, clean(text))
    self.authors[author].add_Post(post)
    self.posts.append(post)
    self.post_dict[post_id] = (post)

  def run_tokenizer(self, tokenizer):
    self.tokenizer = tokenizer
    self.token_index = defaultdict(int)
    for thread in self.threads:
      thread.run_tokenizer(tokenizer)
      for token in thread.token_index:
        self.token_index[token] += thread.token_index[token]
    
class Author(object):
  def __init__(self):
    self.posts = []
    self.threads = []

  def __repr__(self):
    return "<author '%s' (%d posts in %d threads, initiated %d)>" % (self.name, len(self.posts), len(self.all_threads), len(self.threads))

  def __eq__(self, other):
    if isinstance(other, Author):
      return self.name == other.name
    else:
      return self.name == other
    
  @property
  def name(self):
    if len(self.posts) > 0 :
      return self.posts[0].author
    elif len(self.threads) > 0:
      return self.threads[0].author
    else:
      raise ValueError, "Author with no threads and no posts!"

  @property
  def all_threads(self):
    return list(set(p.thread for p in self.posts))

  def add_Post(self, post):
    self.posts.append(post)

  def add_Thread(self, thread):
    self.threads.append(thread)

class Thread(object):
  def __init__(self, id, title, author, date, forum):
    self.id = unicode(id)
    self.title = title
    self.author = author
    self.date = dt.datetime.fromtimestamp(date)
    self.forum = forum
    self.posts = []
    self.post_dict = {}
    self.token_index = None
    self.tokenizer = None
    self.post_authors = set()

  def __eq__(self, other):
    return self.id == other.id

  def __len__(self):
    return len(self.posts)

  def __repr__(self):
    return "<thread %s by %s, %d posts>" % (str(self.id), self.author, len(self.posts))

  def __str__(self):
    o = StringIO()
    print >>o, repr(self)
    for i,p in enumerate(self.posts):
      print >>o, "    %d: %s" % ( i, str(p) )
    return o.getvalue()

  def __contains__(self, item):
    if isinstance(item, Post):
      return item in self.posts
    if isinstance(item, Author):
      return any(item.name == p.author for p in self.posts)

  def __getitem__(self, key):
    return self.post_dict[key]

  def __iter__(self):
    return iter(self.posts)

  @property
  def xml(self):
    b = etree.TreeBuilder()

    b.start('thread', {'id':self.id})

    b.start('title',{})
    b.data(escape(self.title))
    b.end('title')

    b.start('author',{})
    b.data(escape(self.author))
    b.end('author')

    b.start('date',{})
    b.data(str(time.mktime(self.date.timetuple())))
    b.end('date')

    b.end('thread')
    e = b.close()

    for p in self.posts:
      e.append(p.xml)

    return e

  def add_Post(self, id, title, author, date, text):
    post = Post(id, title, author, date, text, self)
    self.posts.append(post)
    self.post_dict[id] = post
    self.post_authors.add(author)
    return post

  def run_tokenizer(self, tokenizer):
    self.tokenizer = tokenizer
    self.token_index = defaultdict(int)
    for post in self.posts:
      post.run_tokenizer(tokenizer)
      for token in post.token_index:
        self.token_index[token] += post.token_index[token]

class PostList(list):
  def __init__(self, *args, **kwargs):
    list.__init__(self, *args, **kwargs)
    self.token_index = None
    self.tokenizer = None

  def run_tokenizer(self, tokenizer):
    self.tokenizer = tokenizer
    self.token_index = defaultdict(int)
    for post in self:
      post.run_tokenizer(tokenizer)
      for token in post.token_index:
        self.token_index[token] += post.token_index[token]

class Post(object):
  def __init__(self, id, title, author, date, text, thread):
    self.id = unicode(id)
    self.title = title
    self.author = author
    self.date = dt.datetime.fromtimestamp(date)
    self.text = text
    self.token_index = None
    self.tokenizer = None
    self.thread = thread

  def __eq__(self, other):
    return self.id == other.id

  def __len__(self):
    return len(self.text)

  def __cmp__(self, other):
    return cmp(self.date, other.date)

  def __repr__(self):
    return "<post %s by '%s'>" % (str(self.id), self.author)

  def __str__(self):
    return "<post %s by '%s' %d sentences>"% (str(self.id), self.author, len(self.sentences))

  @property
  def xml(self):
    b = etree.TreeBuilder()
    b.start('post', {'id':self.id})

    b.start('title',{})
    b.data(escape(self.title))
    b.end('title')

    b.start('author',{})
    b.data(escape(self.author))
    b.end('author')

    b.start('date',{})
    b.data(str(time.mktime(self.date.timetuple())))
    b.end('date')

    b.start('text',{})
    b.data(escape(self.text))
    b.end('text')

    b.end('post')
    tag = b.close()
    # Sanity check to make sure that etree will allow us 
    # to parse this again later.
    f = StringIO()
    etree.ElementTree(tag).write(f)
    etree.fromstring(f.getvalue())
    return tag
  
  @property
  def sentences(self):
    return parse_sentences(self.text)

  def run_tokenizer(self, tokenizer):
    self.tokenizer = tokenizer
    self.token_index = defaultdict(int)
    for token in tokenizer(self.text):
      self.token_index[token] += 1

  def prev_by_thread(self):
    index = self.thread.posts.index(self)
    if index == 0:
      return None
    else:
      return self.thread.posts[index - 1]

  def next_by_thread(self):
    index = self.thread.posts.index(self)
    if index == (len(self.thread.posts) -1):
      return None
    else:
      return self.thread.posts[index + 1]

class Sentence(list):
    """
    Extend the list to store the type of sentence
    Directly from rbp's original code.
    """

    def __init__(self):
        self.end = ''

    def __str__(self):
        return ' '.join(self) + self.end

    def tag(self, end):
        # set ending character of sentence to store type
        self.end = end

def parse_sentences(text):
  """
  Extract sentences from posts
  from rbp's original code
  modifications by mlui
  """
  sentences = []
  # store current sentence
  sentence = Sentence()    
  # store current word
  word = []                    
  
  for i in range(len(text)):
      char = text[i]
      if char in string.letters or char in string.digits:
          word.append(char.lower())
      else:
          if char in '\t ' and word:
              # found word dividor
              sentence.append(''.join(word))
              word = []
          elif char in '?!\n.':
              # '.' complicated as can be used in acronyms or numbers or URLs
              if char == '.' and ((word and (word[-1] in string.uppercase or word[-1] in string.digits)) or (i + 1 < len(text) and text[i+1] in string.letters)):
                  # include '.' for acronym or number
                  word.append(char)
              else:
                  # found end of sentence (and therefore also end of word)
                  # show type of sentence: question/exclamation/statement
                  if word:
                      sentence.append(''.join(word))
                      if char == '\n' and word[-1] == '.':
                          char = '.'
                      word = []
                  if sentence:
                      sentence.tag(char)
                      sentences.append(sentence)
                      sentence = Sentence()
  if word != []:
    sentence.append(''.join(word))
  if sentence != []:
    sentences.append(sentence)
  return sentences

def rbp_tokenize(text):
  sentences = parse_sentences(text)
  words = []
  for s in sentences:
    words.extend(s)
  return words




