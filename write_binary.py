'''
Implements methods to save results into binary files.
'''

import struct
from itertools import chain
import time
from math import log10
import cPickle

import BitVector as bv


def write_sets_binary(sets, filename):
    '''
    Writes the list of bitvectors to a binary file.

    Parameters
    ----------
    sets : iterable of bitvectors
        The sets to store
    filename : string
        The filename to store the results in.

    Notes
    -----
    The used format is the following:
    First 4 bytes for the set id,
    Next 4 bytes for the set size,
    Size * 4 bytes for set items.
    '''

    f = open(filename, 'wb')
    for i, S in enumerate(sets):
        n = S.count_bits_sparse()
        f.write(struct.pack('i', i))
        f.write(struct.pack('i', n))

        bit = -1
        for j in xrange(n):
            bit = S.next_set_bit(bit + 1)
            f.write(struct.pack('i', bit))
    f.close()

def splitmerge(ls, digit):
    buf = [[] for i in range(10)]
    divisor = 10 ** digit
    for (n, x) in ls:
        buf[(n // divisor) % 10].append((n, x))
    return chain(*buf)

def radixsort(ls, fn=splitmerge):
    '''
    Sorts a list in increasing order.

    Parameters
    ----------
    ls : list of tuples
        The list to sort, it has to be a list of tuples, it will be sorted on
        the first item of the tuple

    Returns
    -------
    The sorted list and the dictionary containing the original order
    '''

    return list(reduce(fn, xrange(int(log10(max(abs(val) for (val, x) in ls)) + 1)), ls))

def prepare_for_check(Data, verbose=False):
    '''
    Prepares the list of bitvectors for further analysis.

    It sorts the items of each set by increasing frequency.
    The sets are sorted by increasing size.

    Parameters
    ----------
    Data : iterable of bitvectors
        The data to prepare for the maximality check.
    verbose : bool
        The verbosity of the method. If True, the program will print the
        benchmarks. Default False.
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
    sorted_vectors = radixsort(occurrences)
    if verbose: print time.time() - toc, 'Sorting bit occurences'

    index = {}
    rev_index = {}
    for i in xrange(len(sorted_vectors)):
        index[sorted_vectors[i][1]] = i
        rev_index[i] = sorted_vectors[i][1]

    toc = time.time()
    new_vectors = []
    for vec in new_Data:
        new_vec = bv.BitVector(size=len(vec))
        bit = -1
        for i in xrange(vec.count_bits_sparse()):
            bit = vec.next_set_bit(bit + 1)
            new_vec[index[bit]] = 1

        new_vectors.append(new_vec)
    if verbose: print time.time() - toc, 'Rearranging vectors', len(new_vectors)

    return new_vectors, new_Data
