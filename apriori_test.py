

import sys
import itertools
import time

# Need to dedupe raw vectors

# For regionalization, need to represent vectors as a scalar and modulo by their bucket
# How to make vector into a scalar? Norm of vector? Eigenvalue?

# Some of the data entries are impossible (latitude cannot exceed 180. BTW the negative indicates west)

# From some analysis, height is from 7.2->81.0, width from -109.5->63. 73.8 H-H, 172.5 W-W

# As a first pass on regionalization, consider the following:
""" Suppose we want to group the map into a 10x10 grid
The question becomes "what sector does my x,y belong to"
answer:
73.8 / 10 -> 7.38. So take candidate x / 7.38, truncate to int, that's the x-region. If on the line (modulo = 0), take -1
ditto for y.
result: x*10 + y = region #


"""
REGION_DIMENSION = 20
MIN_SUP = 50
x_interval = 73.8/REGION_DIMENSION
y_interval = 172.5/REGION_DIMENSION

# Next steps:
# - Look into fitness function for assoc rule
# - Dig into dynamic region partitioning

def gatherCoordinateList(inputStr):
  parseStr = inputStr.split(' ')[1]
  if parseStr[-1] == ',':
    parseStr = parseStr[:-1]

  result = []
  parseStr = parseStr.strip()

  for vecStr in parseStr.split(','):
    if len(vecStr):
      currVec = vecStr.replace('(', '').replace(')', '').split(':')
      result.append( (float(currVec[0]), float(currVec[1])) )

  return result

def regionalize(coordinate):

  x_region = int(coordinate[0] / x_interval)
  y_region = int(coordinate[1] / y_interval)

  if coordinate[0] % x_interval == 0:
    x_region -= 1

  if coordinate[1] % y_interval == 0:
    y_region -= 1

  return x_region*REGION_DIMENSION + y_region


def safe_increment(table, key, value=1):
  try:
    table[key] += value
  except KeyError:
    table[key] = value

def gather_new_frequent_items(resultTable, frequent_k_itemsets):
  final_itemsets.append({})
  for key in frequent_k_itemsets:
    if frequent_k_itemsets[key] >= MIN_SUP:
      final_itemsets[-1][key] = frequent_k_itemsets[key] 

def timeseries_candidate_generation(frequent_k_itemsets, chunk_size):
  # We have our L_k, use suffix-prefix to get C_k+1
  candidates = []
  for curr_index, curr in enumerate(frequent_k_itemsets):
    for compare_index, compare in enumerate(frequent_k_itemsets):

      # if last chunk size of item equal to first chunksize of item2, add to cands
      if curr_index != compare_index and curr[(chunk_size*-1):] == compare[:chunk_size]:
        # we found a possible candidate but we need to do a prune check using frequent_k_itemsets
        new_candidate = join_entries(curr, compare, chunk_size)
        required_itemset_checks = itertools.combinations(new_candidate, chunk_size+1)
        if all(item == curr or item == compare or item in frequent_k_itemsets for item in required_itemset_checks):
          candidates.append(new_candidate)

  return candidates

def join_entries(left, right, chunk_size):
  return left + right[chunk_size:]

with open(sys.argv[1], 'r') as vectors, open(sys.argv[2], 'w') as patterns:
  level = 1
  candidate_itemsets = [] # Store C_k before pruning/reading
  final_itemsets = [] # For each level, dict of itemsets

  while level == 1 or len(candidate_itemsets) >= level+1:
    freqs = {}
    # On each level, do the following:
    # - candidate generation
    # - prune
    # - actually scan
    print "Level %d" % level
    if level == 1: # level 1, just build singletons with basic scan
      for line in vectors:
        coords = gatherCoordinateList(line)
        for co in coords:
          region = regionalize(co)
          safe_increment(freqs, region)

      # we have all the singletons. Gather the frequent ones
      gather_new_frequent_items(final_itemsets, freqs)

      # generate candidates for next level here. Cand generation is a little different for first round
      candidate_itemsets = list(itertools.permutations(final_itemsets[0], 2))
      print len(final_itemsets[-1].keys()), "Number of Frequent k itemsets"
      level += 1

    else: # cand gen/prune
      # we are given C_k, , read table, add L_k to final result, generate/prune C_k+1, incr level

      for line in vectors:
        coords = gatherCoordinateList(line)
        regions = [regionalize(co) for co in coords]
        # update counts of candidates we find
        for cand in candidate_itemsets:
          if set(cand).issubset(regions):
            safe_increment(freqs, cand)

      gather_new_frequent_items(final_itemsets, freqs)
      print len(final_itemsets[-1].keys()), "Number of Frequent k itemsets"

      # use prefix-suffix to generate and prune C_k+1 (next level will do the pruning)
      candidate_itemsets = timeseries_candidate_generation(final_itemsets[-1].keys(), level-1)
      print len(candidate_itemsets), "Number of level k+1 Candidates"
      level += 1

    vectors.seek(0)

  for level in final_itemsets:
    for itemset in level:
      patterns.write(str(itemset) + " : " + str(level[itemset]) + "\n")



