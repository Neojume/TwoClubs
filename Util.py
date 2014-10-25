# -*- coding: utf-8 -*-
'''
Implements some utility functions
'''

# Python imports
import sys
import cPickle
from itertools import chain
from math import log10
import numpy as np

# 3rd party libraries
import networkx as nx
import BitVector as bv


def write_sets_binary(sets, filename):
    '''
    Writes the list of bitvectors to a binary file.

    Notes
    -----
    The used format is the following:
    First 4 bytes for the set id,
    Next 4 bytes for the set size,
    Size * 4 bytes for set items.
    '''
    i = 0
    f = open(filename, 'wb')
    for S in sets:
        n = S.count_bits_sparse()
        f.write(struct.pack('i', i))
        f.write(struct.pack('i', n))

        i += 1
        bit = -1
        for j in xrange(n):
            bit = S.next_set_bit(bit + 1)
            f.write(struct.pack('i', bit))
    f.close()


def prepare_for_check(Data, verbose=False):
    '''
    Prepares the list of bitvectors for further analysis.

    It sorts the items of each set by increasing frequency.
    The sets are sorted by increasing size.

    If verbose, the program will print the benchmarks.
    '''

    toc = time.time()
    Data_tuples = [(S.count_bits_sparse(), S) for S in Data]
    if verbose: print time.time() - toc, 'Counting sizes'

    # Sort the list
    toc = time.time()
    sorted_Data = radixsort(Data_tuples)
    if verbose: print time.time() - toc, 'Sorting by size', len(sorted_Data)

    # Retrieve only the bitvectors
    toc = time.time()
    new_Data = [x[1] for x in sorted_Data]
    if verbose: print time.time() - toc, 'Retrieving bitvectors', len(new_Data)

    toc = time.time()
    occurrences = [0 for x in range(len(new_Data[0]))]
    for vec in new_Data:
        bit = -1
        for i in xrange(vec.count_bits_sparse()):
            bit = vec.next_set_bit(bit + 1)
            occurrences[bit] += 1
    if verbose: print time.time() - toc, 'Counting bit occurences'

    toc = time.time()
    occurrences = [(occurrences[i], i) for i in range(len(occurrences))]
    sorted_vectors = radixsort( occurrences )
    if verbose: print time.time() - toc, 'Sorting bit occurences'

    index = {}
    rev_index = {}
    for i in xrange(len(sorted_vectors)):
        index[sorted_vectors[i][1]] = i
        rev_index[i] = sorted_vectors[i][1]

    toc = time.time()
    new_vectors = []
    for vec in new_Data:
        new_vec = bv.BitVector(size = len(vec))
        bit = -1
        for i in xrange(vec.count_bits_sparse()):
            bit = vec.next_set_bit(bit + 1)
            new_vec[ index[bit] ] = 1

        new_vectors.append(new_vec)
    if verbose: print time.time() - toc, 'Rearranging vectors', len(new_vectors)

    return new_vectors, new_Data


def get_club_type(G):
    '''
    Finds the type of 2-club for the given graph. Assumes input graph is a
    2-club.

    Parameters
    ----------
    G : networkx Graph
        The graph to determine the type of

    Returns
    -------
    A string that is either:
        'Coterie'
        'ns-Coterie'
        'Social Circle'
        'Hamlet'
    '''

    A = nx.to_numpy_matrix(G)
    A[A >= 1] = 1 # adjacency matrix with no weights
    A[A < 1] = 0  # adjacency matrix with no weights

    # Find its type
    if len(A) - 1 in np.sum(A, 0):
        if nx.is_biconnected(G):
            return 'ns-Coterie'
        else:
            return 'Coterie'

    elif bool(np.logical_not(np.logical_not(A) * np.logical_not(A)).any()):
        return 'Social circle'
    else:
        return 'Hamlet'


def post_process(G, sets, index_file):
    '''
    Performs some postprocessing on the results.

    Parameters
    ----------
    G : networkx.Graph
        The graph that has been searched in.

    sets : list of bitvectors
        List that contains all sets.

    index_file : file object
        File that contains indices of maximal sets.

    Notes
    -----
    Counts the types of 2-clubs and stores the frequency distribution.
    '''

    # Make dict
    all_clubs = dict()
    search = dict()
    club_types = dict()

    results = dict()
    results['Hamlet'] = []
    results['Social circle'] = []
    results['Coterie'] = []
    results['ns-Coterie'] = []

    sizes = dict()
    sizes['Hamlet'] = dict()
    sizes['Social circle'] = dict()
    sizes['Coterie'] = dict()
    sizes['ns-Coterie'] = dict()

    G_nodes = G.nodes()

    for node in G_nodes:
        search[node] = []

    sets_set_form = []

    # Loop through all maximal indices
    for index in index_file:
        index = int(index)
        current = sets[index]

        # Extract the nodes from the bitvector
        bit = -1
        nodes = []
        size = current.count_bits_sparse()
        for i in xrange(size ):
            bit = current.next_set_bit(bit + 1)
            nodes.append(bit)

        # Add to the sets
        sets_set_form.append(set(nodes))
        all_clubs[index] = nodes

        # Create the subgraph
        current_nodes = []
        for i in nodes:
            node = G_nodes[i]
            current_nodes.append(node)

            search[node].append(index)

        H = nx.subgraph(G, current_nodes)
        club_type = get_club_type(H)
        club_types[index] = club_type
        # Append the result
        results[club_type].append((size, index))

        # Sizes histogram
        if size not in sizes[club_type]:
            sizes[club_type][size] = 1
        else:
            sizes[club_type][size] += 1

    # All results have been indexed by type, now sort by size
    print 'Number of hamlets       :', len(results['Hamlet'])
    print 'Number of social circles:', len(results['Social circle'])
    print 'Number of coteries      :', len(results['Coterie'])
    print 'Number of ns-coteries   :', len(results['ns-Coterie'])

    # Create a dictionary containing all the information
    all_info = dict()
    all_info['nodes'] = G_nodes
    all_info['graph'] = G
    all_info['search'] = search
    all_info['club_types'] = club_types
    all_info['all_clubs'] = all_clubs

    f = open('maximal_clubs.result', 'wb')
    cPickle.dump(all_info, f)
    f.close()


def DROP(connectivity, info):
    '''
    Performs one step of the DROP algorithm as described by Bourjolly [1]_.

    Parameters
    ----------
    connectivity : np.matrix
        The connectivity matrix for this solution.
    info : list of ints
        The information for each vertex whether it is in the solution,
        out of the solution, or undecided.

    Returns
    -------
    The node to remove from the solution.

    References
    ----------
    .. [1] Heuristics for finding k-clubs in an undirected graph.
           J.M. Bourjolly, G. Laporte and G. Pesant.
           Computers & Operational Research. 27(6): 559-569, 2000.
    '''

    # Participating nodes
    nodes = [i for i, k in enumerate(info) if k >= 0]

    # Calculate the q-values
    q = dict()
    all_zero = True
    for i in nodes:
        q[i] = 0
        for j in nodes:
            if connectivity[i, j] == 0:
                q[i] += 1

        if q[i] > 0:
            all_zero = False

    if all_zero: return -1

    # Find node with maximal q of least degree
    to_remove = None
    for i in nodes:
        if info[i] == 1:
            continue
        if to_remove == None:
            to_remove = i
            continue
        if q[i] > q[to_remove]:
            to_remove = i
        elif q[i] == q[to_remove]:
            if connectivity[i, i] < connectivity[to_remove, to_remove]:
                to_remove = i
    return to_remove


def splitmerge(ls, digit):
    buf = [[] for i in range(10)]
    divisor = 10 ** digit
    for (n,x) in ls:
        buf[(n // divisor) % 10].append((n, x))
    return chain(*buf)

def radixsort(ls, fn=splitmerge):
    '''
    Returns a sorted list in increasing order and
    the dictionary containing the original order

    Parameters
    ----------

    ls : list of tuples
        The list to sort, it has to be a list of tuples, it will be sorted on
        the first item of the tuple
    '''
    return list(reduce(fn, xrange(int(log10(max(abs(val) for (val, x) in ls)) + 1)), ls))
