from collections import defaultdict

def author_features(thread):
  author_counts = defaultdict(int)
  for p in thread.posts:
    author_counts[p.author] += 1
  return author_counts
