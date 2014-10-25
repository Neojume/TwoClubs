from distutils.core import setup
import py2exe
import matplotlib
matplotlib.use('wxagg') # overrule configuration


setup(
	windows = ['Viewer.py'],
	data_files = matplotlib.get_py2exe_datafiles(),
	options={'py2exe': {'excludes': ['_gtkagg', '_tkagg'],}}
)
