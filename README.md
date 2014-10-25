Finding 2-clubs
---------------

This repository contains programs to find all 2-clubs in a graph in parallel.
There is also a viewer application to view the results, i.e. the 2-clubs, and 
perform some operations on them.

Used libaries
-------------
- NetworkX 
- BitVector
- WXPython
- Matplotlib

Other dependencies
------------------
We also use the maximality check created by Bayardo and Panda.
This can be found at https://code.google.com/p/google-extremal-sets/

The code assumes the executable ams-cardinality is put in the same directory 
as FindAllClubs.py

How to find 2-clubs? 
--------------------
You can either call the function in a python script or use the commandline interface.

In a python script do the following:

```python
import networkx as nx

from FindAllClubs import find_clubs

# Load your graph, for example in graphml:
G = nx.read_graphml('testgraph.xml')

# Define the number of hubs and their workers.
# The following specifies two hubs each with two workers.
hubs = [2, 2]

# Find the actual clubs, results are stored in a .result file.
find_clubs(G, hubs)
```

To obtain the same via the commandline interface you can call

    python FindAllClubs.py testgraph.xml 2 2

Note that (for now) only the graphml format is supported via commandline.

How to view the results?
------------------------
The viewer is a cross-platform application and can be run on Windows, Linux and Max OS.

To start the viewer via commandline type:
    python Viewer.py

A windows executable can be created using the py2exe libary. To create an executable file, run:
    python setup.py

In the viewer load the result file to view the different two clubs, compare them and obtain some statistics about them.

The result file is a pickled object and can also be read by a python script.

License
-------
This piece of software is provided as is under the GNU Public license.

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
