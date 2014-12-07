#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 12:05:17 2013

@author: Steven
"""

import os.path
import sys
import networkx as nx

import cPickle as pickle
import time
from collections import defaultdict
import argparse

def boroughs_via_cycles(G, minlen=3, maxlen=5):
    """Find simple cycles (elementary circuits) of at least length minlen
    and at most length maxlen of a graph

    An simple cycle, or elementary circuit, is a closed path where no
    node appears twice, except that the first and last node are the same.
    Two elementary circuits are distinct if they are not cyclic permutations
    of each other.

    Parameters
    ----------
    G : NetworkX Graph
       A graph
    minlen : int
       The minimum length of a cycle
    maxlen : int
       The maximum length of a cycle

    Returns
    -------
    A list of circuits, where each circuit is a list of nodes, with the first
    and last node being the same.

    Example:
    >>> G = nx.DiGraph([(0, 0), (0, 1), (0, 2), (1, 2), (2, 0), (2, 1), (2, 2)])
    >>> nx.simple_cycles(G)
    [[0, 0], [0, 1, 2, 0], [0, 2, 0], [1, 2, 1], [2, 2]]

    See Also
    --------
    cycle_basis (for undirected graphs)

    Notes
    -----
    The implementation follows pp. 79-80 in [1]_.

    The time complexity is O((n+e)(c+1)) for n nodes, e edges and c
    elementary circuits.

    References
    ----------
    .. [1] Finding all the elementary circuits of a directed graph.
       D. B. Johnson, SIAM Journal on Computing 4, no. 1, 77-84, 1975.
       http://dx.doi.org/10.1137/0204007

    See Also
    --------
    cycle_basis
    """
    # Jon Olav Vik, 2010-08-09
    # Edited by Steven Laan, 2013-01-23
    def _unblock(thisnode):
        """Recursively unblock and remove nodes from B[thisnode]."""
        if blocked[thisnode]:
            blocked[thisnode] = False
            while B[thisnode]:
                _unblock(B[thisnode].pop())

    def circuit(thisnode, startnode, component):
        closed = False # set to True if elementary path is closed
        path.append(thisnode)
        if len(path) <= maxlen:
            blocked[thisnode] = True

            for nextnode in component[thisnode]: # direct successors of thisnode
                if nextnode == startnode:
                    if len(path) >= minlen:
                        add_cycle(path + [startnode])
                    closed = True
                elif not blocked[nextnode]:
                    if circuit(nextnode, startnode, component):
                        closed = True
            if closed:
                _unblock(thisnode)
            else:
                for nextnode in component[thisnode]:
                    if thisnode not in B[nextnode]:
                        B[nextnode].append(thisnode)
        path.pop() # remove thisnode from path
        return closed

    def add_cycle(cycle):
        my_matches = []
        cycle_set = set(cycle)
        for borough in boroughs:
            overlap = cycle_set & borough
            found = False
            for node in overlap:
                for neighbor in G.neighbors(node):
                    if neighbor in overlap:
                        my_matches.append(borough)
                        found = True
                        break
                if found:
                    break
        for match in my_matches:
            cycle_set = cycle_set | match
            boroughs.remove(match)
        if cycle_set not in boroughs:
            boroughs.append(cycle_set)

    path = [] # stack of nodes in current path
    blocked = defaultdict(bool) # vertex: blocked from search?
    B = defaultdict(list) # graph portions that yield no elementary circuit
    boroughs = [] # list to accumulate the circuits found

    # Johnson's algorithm requires some ordering of the nodes.
    # They might not be sortable so we assign an arbitrary ordering.
    ordering = dict(zip(G, range(len(G))))
    for s in ordering:
        # Build the subgraph induced by s and following nodes in the ordering
        subgraph = G.subgraph(node for node in G
                              if ordering[node] >= ordering[s])
        # Find the strongly connected component in the subgraph
        # that contains the least node according to the ordering
        strongcomp = nx.connected_components(subgraph)
        mincomp = min( strongcomp,
                    key = lambda nodes: min(ordering[n] for n in nodes))
        component = G.subgraph(mincomp)
        if component:
            # smallest node in the component according to the ordering
            startnode = min(component, key = ordering.__getitem__)
            for node in component:
                blocked[node] = False
                B[node][:] = []
            dummy = circuit(startnode, startnode, component)

    return sorted(boroughs, key = len, reverse = True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('graph', help='The graph to find the boroughs of.')
    parser.add_argument('-o', '--output', help='The file to put the results in.', default='boroughs_result.pickle')
    parser.add_argument('-t', '--type', help='The type of the output.', default='pickle')
    parser.add_argument('-g', '--graphics', help='Visualize the boroughs.', action='store_true')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    G = nx.read_graphml(args.graph)

    if args.verbose:
        print 'starting search (%d nodes)' % len(G.nodes())
    start = time.time()
    boroughs = boroughs_via_cycles(G)
    if args.verbose:
        print 'took', time.time() - start, 'seconds'

    num_boroughs = len(boroughs)
    if args.verbose:
        print 'Boroughs found:', num_boroughs

    if args.type == 'graphml':
        extension = os.path.basename(args.output).split(os.path.extsep)[-1]
        index = len(extension) + len(os.path.extsep)
        filename = os.path.basename(args.output)[:-index]

        for i, borough in enumerate(boroughs):
            writer = nx.GraphMLWriter(graph=nx.subgraph(G, borough))
            f = open(filename + str(i) + os.path.extsep + extension, 'w')
            writer.dump(f)
            f.close()
    else:
        f = open(args.output, 'w')
        pickle.dump(boroughs, f)
        f.close()

    if args.graphics:
        import matplotlib.pyplot as plt

        pos = nx.spring_layout(G)
        for i,b in enumerate(boroughs):
            H = nx.subgraph(G, b)
            nx.draw_networkx_edges(H, pos)
            c=[i]*nx.number_of_nodes(H)
            nx.draw_networkx_nodes(H, pos, node_color=c, vmin=0, vmax=num_boroughs, cmap=plt.cm.hsv)
            nx.draw_networkx_labels(H, pos)
        plt.show()

