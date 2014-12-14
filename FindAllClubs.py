# -*- coding: utf-8 -*-
'''
Implementation of parallel tree search of all 2-clubs.

Copyright (C) 2012  Steven Laan

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see http://www.gnu.org/licenses/
'''

# Python imports
import sys
import time
import pickle
import subprocess
import argparse
import multiprocessing as mp
from copy import deepcopy

# 3rd party libaries
import networkx as nx
import BitVector as bv

# Own imports
from MasterHub import Master, Node, Model

from Util import *
from Drivers import find_drivers_id


class TwoClubNode(Node):

    '''
    A node in the 2-club search tree.
    '''

    def __init__(self, C, info, terminal):
        '''
        Creates a TwoClubNode.

        Parameters
        ----------
        C : np.matrix
            The connectivity matrix associated with this node.
        info : list
            The information for which vertices are in the current
            solution, which are out and which are still undecided.
        terminal : bool
            Whether this node is a leaf node of the tree.
        '''

        super(TwoClubNode, self).__init__(terminal)

        self.info = info
        self.C = C

class TwoClubModel(Model):

    '''
    The tree search model for the all 2-clubs problem. It specifies the initial
    state and how to expand nodes.
    '''

    def __init__(self, G):
        '''
        Creates a TwoClubProblem for the given graph.

        Parameters
        ----------
        G : networkx.Graph
            The graph to find the 2-clubs of.
        '''

        n = nx.number_of_nodes(G)
        self.drivers, _ = find_drivers_id(G)
        Adj = nx.adj_matrix(G)

        # Create the individual adjacency matrices
        self.A = dict()
        for i in xrange(n):
            self.A[i] = Adj[i,:].transpose() * Adj[i,:]

        # Connectivity matrix
        C = Adj + Adj * Adj
        del Adj

        # First info vector
        info = [0 for i in xrange(n)]
        self.first_node = TwoClubNode(C, info, False)

    def process_node(self, node_to_process):
        '''
        Processes a (partial) solution node.

        Parameters
        ----------
        node_to_process : TwoClubNode
            The node that is to be processed

        Returns
        -------
        new_nodes : list
            The list containing the children of the processed node.
            Can be empty.
        '''

        C = node_to_process.C
        info = node_to_process.info

        # Number of nodes
        n = len(info)

        # Feasibility check
        keep = [i for i in xrange(n) if info[i] == 1]
        for i in keep:
            for j in keep:
                if C[i,j] == 0:
                    # Unfeasible
                    return []

        # Call DROP to branch
        to_remove = DROP(C, info)

        # Termination check
        if to_remove == -1:
            return [TwoClubNode(None, info, True)]

        new_nodes = []

        # Branch 2
        keep_info = list(info)
        keep_info[to_remove] = 1
        keep_C = deepcopy(C)

        # Remove nodes that are not in the 2 neigborhood
        feasible = True
        for i in xrange(n):
            if C[i,to_remove] == 0:
                if keep_info[i] == 1:
                    feasible = False
                    break
                elif keep_info[i] == 0:
                    # Update problem parameters
                    keep_C -= self.A[i]
                    keep_info[i] = -1
        if feasible:
            new_nodes.append(TwoClubNode(keep_C, keep_info, False))

        # Branch 1
        feasible = True
        to_remove_list = [to_remove]
        if to_remove in self.drivers:
            for lifter in self.drivers[to_remove]:
                if info[lifter] == 1:
                    feasible = False
                    break
                elif info[lifter] == 0:
                    to_remove_list.append(lifter)
        if feasible:
            rem_C = deepcopy(C)
            for node in to_remove_list:
                rem_C -= self.A[node]
                info[node] = -1
            new_nodes.append(TwoClubNode(rem_C, list(info), False))

        return new_nodes

    def get_root(self):
        '''
        Returns the root node of the search tree.
        '''

        return self.first_node


def find_candidates(G, hubs):
    '''
    Find the candidate 2-clubs for the given graph using the specified
    hub-structure.

    Parameters
    ----------
    G : NetworkX Graph
        The input graph
    hubs: List of integers
        The hub structure. Each list item is a hub,
        the value of each item specifies the number of workers.

    Returns
    -------
    A tuple (time, candidates), wehere time is the time the computation took
    and candidates is the list of candidates.
    '''

    # Instantiate the model with the given graph
    model = TwoClubModel(G)

    # Store the current time and start the computation
    t = time.time()
    m = Master(model, hubs, max_len = 8)

    return time.time() - t, m.answers


def find_clubs(G, hubs):
    '''
    Find the 2-clubs of the given graph using the specified hub-structure.

    Parameters
    ----------
    G : NetworkX Graph
        The input graph
    hubs: List of integers
        The hub structure. Each list item is a hub,
        the value of each item specifies the number of workers.

    Returns
    -------
    Nothing (at the moment). The found 2-clubs are stored in
    'maximal_clubs.result'
    '''
    time, candidates = find_candidates(G, hubs)

    answers = []
    for ans in candidates:
        answers.append(bv.BitVector(bitlist = [make_binary(i) for i in ans.info]))

    new_data, sorted_data = prepare_for_check(answers)
    write_sets_binary(new_data, 'binary_file.temp')

    if sys.platform.startswith('linux'):
        subprocess.check_call(['./ams-cardinality','binary_file.temp'])
    elif sys.platform.startswith('win'):
        subprocess.check_call(['ams-cardinality.exe','binary_file.temp'])

    post_process(G, sorted_data, open('output.txt', 'r' ))


if __name__ == '__main__':
    mp.freeze_support()

    parser = argparse.ArgumentParser(description='Compute 2-clubs of a graph.')
    parser.add_argument('graph')
    parser.add_argument('hubs', metavar='Hub', type=int, nargs='+',
                       help='number of workers for the hub')
    group = parser.add_argument_group()
    group.add_argument('-b','--borough', help='The borough result file to use.')
    group.add_argument('-bn','--borough_number',
        help='The id number of the borough. Default 0 = largest.', default = 0)

    args = parser.parse_args()

    G = nx.read_graphml(args.graph)

    if args.borough:
        boroughs = pickle.load(open(args.borough))
        B = nx.Graph()
        B.add_edges_from(boroughs[args.borough_number])
        find_clubs(B, args.hubs)
    else:
        find_clubs(G, args.hubs)

