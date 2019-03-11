from distutils.core import setup
setup(
    name = "pylnk",
    version = "0.2",
    py_modules = ["pylnk"],
    description = "Windows LNK File Parser and Creator",
    author = "Tim-Christian Mundt",
    author_email = "dev@tim-erwin.de",
    url = "http://sourceforge.net/projects/pylnk/",
    download_url = "http://sourceforge.net/projects/pylnk/files/",
    keywords = ["lnk", "shortcut", "windows"],
    license = "GNU Library or Lesser General Public License (LGPL)",
    classifiers = [
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
    long_description = """\
Python library for reading and writing Windows shortcut files (.lnk)

This library can parse .lnk files and extract all relevant information from
them which is especially helpful if you need to do this on a non-ms-windows
machine. Parsing a .lnk file yields a LNK object which can be altered and saved
again. Moreover, .lnk file can be created from scratch be creating a LNK
object, populating it with data and then saving it to a file. As that
process requires some knowledge about the internals of .lnk files, some
convenience functions are provided.

Limitation: Windows knows lots of different types of shortcuts which all have
different formats. This library currently only supports shortcuts to files and
folders on the local machine. 
"""
)
