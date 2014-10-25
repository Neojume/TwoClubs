# -*- coding: utf-8 -*-
'''
Implements the DROP heuristic of Bourjolly et al. using a matrix
implementation.
'''


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
    nodes = [ i for i, k in enumerate(info) if k >= 0 ]

    # Calculate the q-values
    q = dict()
    all_zero = True
    for i in nodes:
        q[i] = 0
        for j in nodes:
            if connectivity[i,j] == 0:
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
            if connectivity[i,i] < connectivity[to_remove,to_remove]:
                to_remove = i
    return to_remove
