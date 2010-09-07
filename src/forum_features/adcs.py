import re
from DataModel import rbp_tokenize, PostList

def ADCS_partition_thread(thread):
  initialPost = PostList()
  firstResponse = PostList()
  allResponses = PostList()
  finalPostInit = PostList()


  # Adapted from rbp's implementation
  feedback_received = False

  ordered_posts = sorted(thread.posts)
  #initiator = thread.author
  # We go with rbp's definition instead.
  initiator = ordered_posts[0].author
  
  for post in ordered_posts:
    if not feedback_received:
      if post.author == initiator:
        initialPost.append(post)
      else:
        firstResponse.append(post)
        feedback_received = True
    elif post.author == initiator:
      # Final post from the initiator seen so far.
      finalPostInit = PostList([post])
    else:
      allResponses.append(post)

  result = dict( initialPost = initialPost
               , firstResponse = firstResponse
               , allResponses = allResponses
               , finalPostInit = finalPostInit
               )
  return result



additive_features = [ 'distribution'
                    , 'beginner'
                    , 'emoticons'
                    , 'version_numbers'
                    , 'urls'
                    ]

post_proportion_features = [ 'question_sentence'
                           , 'exclaim_sentence'
                           , 'period_sentence'
                           , 'other_sentence'
                           ]

part_proportion_features = [ 'word_prop'
                           , 'sentence_prop'
                           , 'first_question_ratio'
                           ]

positional_features = [ 'first_post_prop'
                      , 'last_post_prop'
                      ]

sections = [ 'initialPost'
           , 'firstResponse'
           , 'allResponses'
           , 'finalPostInit'
           ]

def ADCS_Thread_features(thread):
  thread.run_tokenizer(rbp_tokenize)
  parts = ADCS_partition_thread(thread)
  features = {}
  
  total_words = 0.0
  total_sentences = 0.0
  total_posts = 0.0
  for part in parts:
    features[part] = ADCS_PostList_features(parts[part])
    total_words += features[part]['words']
    total_sentences += features[part]['sentence']
    total_posts += features[part]['posts']


  last_post = 0 # Keep track of the index of the last post we have processed
  for part in sections:
    features[part]['word_prop']     = features[part]['words'] / total_words
    features[part]['sentence_prop'] = features[part]['sentence'] / total_sentences
    features[part]['first_question_ratio'] = features[part]['sentence'] / features[sections[0]]['sentence']
    
    # Positional features
    # The first post of this part is one more than the last post of the last part
    features[part]['first_post_prop'] = last_post + 1 / total_posts 
    # The last post of this part is the last post of the last part plus the 
    # number of posts in this part
    last_post += features[part]['posts']
    features[part]['last_post_prop' ] = last_post / total_posts


  # TODO: 
  #       Prop of code sentences
 
  fv = {} 
  f_names = additive_features + post_proportion_features + part_proportion_features + positional_features
  for section in sections:
    section_f = features[section]
    for f_name in f_names:
      fv[section+'_'+f_name] = section_f[f_name]
  return fv

def ADCS_PostList_features(postlist):
  features = {} 
  features['posts'] = len(postlist)
  post_features = [ ADCS_Post_features(p) for p in postlist ]

  for f in additive_features + ['words', 'sentence']:
    features[f] = sum( pf[f] for pf in post_features )

  # TODO: Proportion of code sentences
  for f in post_proportion_features:
    total = sum( pf[f] for pf in post_features )
    # Calculate as a proportion of total sentences
    features[f] = (float(total) / features['sentence']) if features['sentence'] is not 0 else 0.0
    
  sentence_lengths = []
  word_lengths = []
  for p in postlist:
    for s in p.sentences:
      sentence_lengths.append(len(s))
      for w in s:
        word_lengths.append(len(w))

  try:
    features['avg_sentence'] = sum(sentence_lengths) / float(len(sentence_lengths))
    features['avg_word'] = sum(word_lengths) / float(len(word_lengths))
  except ZeroDivisionError:
    features['avg_sentence'] = 0
    features['avg_word'] = 0

  return features


def ADCS_Post_features(post):
  # Based on rbp's code. Trying to reproduce ADCS results as faithfully
  # as possible
  features = {}

  # tokenize if this has not been done yet
  if post.token_index is None:
    post.run_tokenizer(rbp_tokenize)

  # mention of distribution
  features['distribution'] = False
  for word in ["redhat", "rh", "fc" "fedora core", "ubuntu", "debian", "suse", "gentoo", "slackware"]:
    if word in post.token_index:
      features['distribution'] = True

  # mention of "beginner title"
  features['beginner'] = False
  for word in ["noob", "noobie", "newb", "newbie", "n00b", "n00bie"]:
    if word in post.token_index:
      features['beginner'] = True

  # emoticon presence
  features["emoticons"] = re.compile("img src=", re.IGNORECASE).search(post.text) is not None
  
  # version numbers
  features["version_numbers"] = re.compile("\d+\.\d?").search(post.text) is not None

  # urls
  features["urls"] = re.compile("(http|www\.)\S+\.\S+").search(post.text) is not None

  # sentence types
  features["words"] = 0
  features["sentence"] = 0
  features["question_sentence"] = 0
  features["exclaim_sentence"] = 0
  features["period_sentence"] = 0
  features["other_sentence"] = 0
  for s in post.sentences:
    features["words"] += len(s)
    features["sentence"] += 1
    if s.end == '?':
      features["question_sentence"] += 1
    elif s.end == '!':
      features["exclaim_sentence"]  += 1
    elif s.end == '.':
      features["period_sentence"]   += 1
    else:
      features["other_sentence"]    += 1

  return features
      

