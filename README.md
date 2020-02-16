# PyLnk 3
Python library for reading and writing Windows shortcut files (.lnk).  
Converted to support python 3.

This library can parse .lnk files and extract all relevant information from
them. Parsing a .lnk file yields a LNK object which can be altered and saved
again. Moreover, .lnk file can be created from scratch be creating a LNK
object, populating it with data and then saving it to a file. As that
process requires some knowledge about the internals of .lnk files, some
convenience functions are provided.

Limitation: Windows knows lots of different types of shortcuts which all have
different formats. This library currently only supports shortcuts to files and
folders on the local machine. 

## Changes
**0.3.0**  
added support links to UWP apps  
**0.2.1**  
released to PyPI  
**0.2.0**  
converted to python 3  
