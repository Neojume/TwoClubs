'''
Implements algorithms to find the drivers of a graph.
A driver is a node whose ego-network is not contained in
the ego-network of any other node.
'''

import string
import numpy as np
from copy import deepcopy

import networkx as nx

def find_drivers(G):
    '''
    Finds the lifters and drivers in a graph.

    Parameters
    ----------
    G : networkx.Graph
        The graph to find the drivers of

    Returns
    -------
    (drivers, peers) : tuple
        A tuple containing the drivers and peers of the network.
        A driver is a node whose ego-network is not contained in
        the ego-network of any other node.
        Peers are nodes whose ego-networks coincide. Only one of
        the peers is mentioned in the driver set.
    '''

    nodes = G.nodes()
    N = len(nodes)
    A = nx.adjacency_matrix(G) + np.eye(N)

    items = dict()
    driver_candidates = dict()
    for i in xrange(N):
        items[i] = set([j for j in xrange(N) if A[i,j]])
        driver_candidates[nodes[i]] = set()

    for i in xrange(N):
        # Temporarily remove center
        items[i].remove(i)

        for j in xrange(N):
            if i == j:
                continue

            # If all items of i are in j, i is a lifter of j
            if items[i] < items[j]:
                driver_candidates[nodes[j]].add(nodes[i])

        # Add center back
        items[i].add(i)

    drivers = driver_candidates.copy()
    peers = dict()

    for i in xrange(N):
        peers[nodes[i]] = set()

        for j in xrange(N):
            if i == j:
                continue

            set_A = items[i] - set([nodes[j]])
            set_B = items[j] - set([nodes[i]])

            if  set_A == set_B:
                peers[nodes[i]].add(nodes[j])
            elif nodes[i] in driver_candidates[nodes[j]]:
                del drivers[nodes[i]]
                break

    return drivers, peers


def find_drivers_id(G):
    '''
    Finds the lifters and drivers in a graph.

    Parameters
    ----------
    G : networkx.Graph
        The graph to find the drivers and lifters of

    Returns
    -------
    drivers : dict
        dict containing IDs of the lifters of each driver
    '''

    nodes = G.nodes()
    N = len(nodes)
    A = nx.adjacency_matrix(G) + np.eye(N)

    items = dict()
    driver_candidates = dict()
    for i in xrange(N):
        items[i] = set([j for j in xrange(N) if A[i,j]])
        driver_candidates[i] = set()

    for i in xrange(N):
        # Temporarily remove center
        items[i].remove(i)

        for j in xrange(N):
            if i == j:
                continue

            # If all items of i are in j, i is a lifter of j
            if items[i] < items[j]:
                driver_candidates[j].add(i)

        # Add center back
        items[i].add(i)

    drivers = driver_candidates.copy()
    peers = dict()

    for i in xrange(N):
        peers[i] = set()

        for j in xrange(N):
            if i == j:
                continue

            set_A = items[i] - set([j])
            set_B = items[j] - set([i])

            if  set_A == set_B:
                peers[i].add(j)
            elif i in driver_candidates[j]:
                del drivers[i]
                break

    # TODO: Remove peers to obtain minimal driver set
    return drivers, peers
