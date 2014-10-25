# -*- coding: utf-8 -*-
'''
Implements different methods to post-process results, such as sorting.
'''

import sys
import cPickle
from itertools import chain
from math import log10
import numpy as np

import networkx as nx


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

    A = nx.to_numpy_matrix( G )
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

    f = open( 'maximal_clubs.result', 'wb' )
    cPickle.dump( all_info, f )
    f.close()
