# -*- coding: utf-8 -*-
'''
Implementation of a Master-Hub-Worker structure for parallel tree search.

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

import multiprocessing as mp

from Queue import Empty
from copy import deepcopy

# Define signals
SIGNAL_NODE = 0
SIGNAL_DONE = 1
SIGNAL_IDLE = 2
SIGNAL_BUSY = 3
SIGNAL_ANSWERS = 4

# Define shorthands
SIG_IDLE = (SIGNAL_IDLE, None)
SIG_DONE = (SIGNAL_DONE, None)
SIG_BUSY = (SIGNAL_BUSY, None)

class Worker(mp.Process):
    '''
    The worker class. Instances of this class are the main processing power of
    the system.
    '''

    def __init__(self, model, queue, feed_queue, max_len = 10):
        '''
        Initializes the worker.

        Parameters
        ----------
        model : Model object
            The model of the problem that is being solved. The model contains
            the code for processing of nodes.
        queue : mp.Queue
            The main queue to get jobs from. In the case of the worker this is
            the queue of the hub.
        feed_queue : mp.Queue
            The queue to feed back results and nodes to the hub.
        max_len : int
            The maximum number of items that can be on a workers private queue,
            before items are pushed back to the hub. Acts as a means of load
            balancing. Default 10.
        '''

        # Base class initialization
        mp.Process.__init__(self)

        self.answers = []
        self.main_queue = queue
        self.feed_queue = feed_queue
        self.stack = []
        self.model = deepcopy(model)
        self.max_stack_size = max_len

    def run(self):
        '''
        Starts the worker process.
        '''

        for _, item in iter(self.main_queue.get, SIG_DONE):
            self.stack.append(item)
            self.feed_queue.put(SIG_BUSY)

            # Don't bother the main queue while we got items
            while len(self.stack):
                node = self.stack.pop()

                self.process_node(node)

                # Check for overflow
                if len(self.stack) > self.max_stack_size:
                    # Put half of the things on the stack on the main queue
                    for i in xrange(len(self.stack) / 2):
                        self.feed_queue.put((SIGNAL_NODE, self.stack.pop()))

            # No more items in the stack, signal the main queue
            self.feed_queue.put(SIG_IDLE)

        # This process isn't going to put anything in the queues anymore
        self.main_queue.close()
        self.feed_queue.put((SIGNAL_ANSWERS, self.answers))

    def process_node(self, node):
        '''
        Processes the given node. This results in either putting new nodes on
        the private stack or appending answers to the answer.

        Parameters
        ----------
        node : node object
            The node to be processed.
        '''
        new_nodes = self.model.process_node(node)

        for new_node in new_nodes:
            if new_node.terminal:
                # Solution found!
                self.answers.append(new_node)
            else:
                self.stack.append(new_node)

class Hub(mp.Process):

    '''
    The intermediate Hub class. This class has a couple of workers in its pool,
    for which it provides jobs. If idle, the hub can perform some work as well.
    '''

    def __init__(self, model, queue, feed_queue, num_workers = 1, max_len = 10):
        '''
        Create an instance of a hub.

        Parameters
        ----------
        model : model object
            The model of the problem that is solved. The model provides the
            procedures to process a node.
        queue :  mp.Queue
            The main queue to get jobs from. In the case of the hub, this is
            the queue from the master.
        feed_queue : mp.Queue
            The queue to feed answers back to the master.
        num_workers : int
            The number of workers this hub has. Default 1.
        max_len : int
            The maximum length of the job queue before jobs are pushed back to
            the master. Default 10.
        '''

        # Base class initialization
        super(Hub, self).__init__()

        self.workers = []
        self.main_queue = queue
        self.queue = mp.Queue()
        self.feed_queue = feed_queue
        self.model = deepcopy(model)
        self.max_len = max_len

        self.answers = []
        self.idle = True
        self.done = False
        self.idle_workers = num_workers
        self.tasks_busy = 0
        self.tasks_accepted = 0

        # Create all workers and start them
        for i in range(num_workers):
            q = mp.Queue()
            worker = Worker(self.model, self.queue, q, max_len = max_len)
            self.workers.append(q)
            worker.start()

    def run(self):
        '''
        Starts the hub process.
        '''

        # Get a first item
        self.get_item()

        while not self.done:
            # Try to get another item
            try:
                self.get_item(False)
            except Empty:
                pass

            if self.idle:
                continue
            if self.done:
                break

            # Handle input of workers
            self.handle_queues()

            # Check for idleness
            if not self.idle:
                if self.tasks_busy == 0:
                    # Signal master, that this chain is idle
                    self.feed_queue.put((SIGNAL_IDLE, self.tasks_accepted))
                    self.tasks_accepted = 0
                    self.idle = True

            while self.tasks_busy > len(self.workers):
                # Check for overflow
                if self.queue.qsize() > self.max_len:
                    try:
                        for i in range(self.max_len / 2):
                            item = self.queue.get()
                            self.tasks_busy -= 1
                            self.feed_queue.put(item)
                    except Empty:
                        # Queue got empty during emptying
                        pass

                # Handle input of workers
                self.handle_queues()

        # We're done! Signal workers we're done
        for _ in self.workers:
            self.queue.put(SIG_DONE)

        # Retrieve answers from workers
        for queue in self.workers:
            signal, answers = queue.get()
            if signal != SIGNAL_ANSWERS:
                raise Exception('Wrong signal: got %d expected %d' % (signal, SIGNAL_ANSWERS))
            self.answers.extend(answers)

        # Send the answers to the master
        self.feed_queue.put((SIGNAL_ANSWERS, self.answers))

    def handle_queues(self):
        '''
        Retrieves one item of each worker queue and processes it.
        '''

        for queue in self.workers:
            try:
                sig, item = queue.get_nowait()
                if sig == SIGNAL_NODE:
                    self.queue.put((sig, item))
                    self.tasks_busy += 1
                elif sig == SIGNAL_IDLE:
                    self.idle_workers += 1
                    self.tasks_busy -= 1
                elif sig == SIGNAL_BUSY:
                    self.idle_workers -= 1
                elif sig == SIGNAL_ANSWERS:
                    self.answers.extend(item)
            except Empty:
                pass

    def get_item(self, block = True):
        '''
        Tries to retrieve an item from the main queue and processes it.

        Parameters
        ----------
        block : bool
            Whether to wait for an item, or continue if no item is
            available. Default True.
        '''

        try:
            sig, item = self.main_queue.get(block = block)
            if sig == SIGNAL_NODE:
                self.queue.put((sig, item))
                self.tasks_accepted += 1
                self.tasks_busy += 1
                if self.idle:
                    self.feed_queue.put(SIG_BUSY)
                    self.idle = False
            elif sig == SIGNAL_DONE:
                self.done = True
            else:
                raise Exception('Wrong signal: got %d' % (sig,))
        except Empty:
            pass


class Master(object):

    '''
    The master of the search. Starts the hubs and collects the results.
    '''

    def __init__(self, model, hub_division, max_len = 10):
        '''
        Creates an instance of the master.

        Parameters
        ----------
        model : model object
            The model of the problem that is solved. The model provides
            the methods to process a node.
        hub_division : list of ints
            The specification of the hubs and workers. Each integer in
            the list is a hub. The value of the integer is the number
            of workers for that hub. For example [2,3] means two hubs,
            one with 2 workers and one with 3.
        max_len : int
            The maximum length for a queue of the hubs and workers,
            before they start pushing back. Default 10.
        '''
        self.model = model
        self.queue = mp.Queue()
        self.hubs = []
        self.answers = []
        self.idle_hubs = len(hub_division)

        self.queue.put((SIGNAL_NODE, model.get_root()))
        self.tasks_busy = 1
        done = False

        # Create all workers and start them
        for i in hub_division:
            q = mp.Queue()
            hub = Hub(model, self.queue, q, num_workers = i, max_len = max_len)
            self.hubs.append(q)
            hub.start()

        # Main loop
        while not done:
            # Handle input of workers
            self.handle_queues()

            # Check for completion
            if self.tasks_busy == 0:
                done = True

        # We're done! Signal hubs we're done
        for _ in self.hubs:
            self.queue.put(SIG_DONE)

        # Retrieve answers from hubs
        for queue in self.hubs:
            sig, answers = queue.get()
            if sig != SIGNAL_ANSWERS:
                raise Exception('Wrong signal: got %d expected %d' % (sig, SIGNAL_ANSWERS))
            self.answers.extend(answers)

    def handle_queues(self):
        '''
        Retrieves one item of each worker queue and processes it.
        '''

        for queue in self.hubs:
            try:
                sig, item = queue.get_nowait()
                if sig == SIGNAL_NODE:
                    self.queue.put((sig, item))
                    self.tasks_busy += 1
                elif sig == SIGNAL_IDLE:
                    self.idle_hubs += 1
                    self.tasks_busy -= item
                elif sig == SIGNAL_BUSY:
                    self.idle_hubs -= 1
                else:
                    raise Exception('Wrong signal: got %d' % (sig,))
            except Empty:
                pass


class Model(object):

    '''
    Abstract base class for a parallel tree search model.
    '''

    def process_node(self, node):
        '''
        Processes a (partial) solution node.

        Parameters
        ----------
        node_to_process : Node object
            The node that is to be processed

        Returns
        -------
        new_nodes : list
            The list containing the children of the processed node.
            Can be empty.
        '''

        raise NotImplementedError

    def get_root_node(self):
        '''
        Returns the root node of the search tree.
        '''

        raise NotImplementedError


class Node(object):

    '''
    Base class for a node of the search tree.
    '''

    def __init__(self, terminal):
        '''
        Creates a Node of the search tree

        Parameters
        ----------
        terminal : bool
            Whether this node is a leaf node of the tree.
        '''

        self.terminal = terminal
