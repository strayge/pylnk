# PyLnk 3

[![PyPI version shields.io](https://img.shields.io/pypi/v/pylnk3.svg)](https://pypi.python.org/pypi/pylnk3/)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/pylnk3.svg)](https://pypi.python.org/pypi/pylnk3/)
[![PyPI download month](https://img.shields.io/pypi/dm/pylnk3.svg)](https://pypi.python.org/pypi/pylnk3/)

Python library for reading and writing Windows shortcut files (.lnk).  
Converted to support python 3.  
[Original](https://sourceforge.net/p/pylnk/code/HEAD/tree/trunk/pylnk.py) version written by Tim-Christian Mundt.  

This library can parse .lnk files and extract all relevant information from
them. Parsing a .lnk file yields a LNK object which can be altered and saved
again. Moreover, .lnk file can be created from scratch be creating a LNK
object, populating it with data and then saving it to a file. As that
process requires some knowledge about the internals of .lnk files, some
convenience functions are provided.

Limitation: Windows knows lots of different types of shortcuts which all have
different formats. This library currently only supports shortcuts to files and
folders on the local machine.

## CLI

Mainly tool has two basic commands.

#### Parse existed lnk file

```help
pylnk3 parse [-h] filename [props [props ...]]

positional arguments:
  filename    lnk filename to read
  props       props path to read

optional arguments:
  -h, --help  show this help message and exit
```

#### Create new lnk file

```help
usage: pylnk3 create [-h] [--arguments [ARGUMENTS]] [--description [DESCRIPTION]] [--icon [ICON]]
                     [--icon-index [ICON_INDEX]] [--workdir [WORKDIR]] [--mode [{Maximized,Normal,Minimized}]]
                     target name

positional arguments:
  target                target path
  name                  lnk filename to create

optional arguments:
  -h, --help            show this help message and exit
  --arguments [ARGUMENTS], -a [ARGUMENTS]
                        additional arguments
  --description [DESCRIPTION], -d [DESCRIPTION]
                        description
  --icon [ICON], -i [ICON]
                        icon filename
  --icon-index [ICON_INDEX], -ii [ICON_INDEX]
                        icon index
  --workdir [WORKDIR], -w [WORKDIR]
                        working directory
  --mode [{Maximized,Normal,Minimized}], -m [{Maximized,Normal,Minimized}]
                        window mode
  --file                threat target as file (by default guessed by dot in target)
  --directory           threat target as directory (by default guessed by dot in target)
```

#### Examples
```sh
# windows
pylnk3 p filename.lnk
pylnk3 c c:\prog.exe shortcut.lnk
pylnk3 c \\192.168.1.1\share\file.doc doc.lnk
pylnk3 create c:\1.txt text.lnk -m Minimized -d "Description"
# linux (escaped backslashes)
pylnk3 create 'c:\\dir\\file.txt' text.lnk -m Minimized -d "Description"
```

## Changes

**1.0.0a1**  
split single `pylnk3.py` to separated modules  
[FIX] fixed building links for non-existing locally paths (guessing target type by dot in name)  
added `--file` / `--directory` create command options to override target type guessing  

**0.4.2**  
changed logic for Lnk.path choose (in case of different paths presents at different structures)  
read links with root as GUID of KNOWN_FOLDER  
[FIX] disabled padding for writing LinkInfo.local_base_path  

**0.4.0**  
added support for network links  
reworked CLI (added more options for creating links)  
added entry point for call tool just like `pylnk3`  
[FIX] allow build links for non-existed (from this machine) paths  
[FIX] correct building links on Linux (now expect Windows-like path)  
[FIX] fixed path priority at parsing with both local & remote presents  

**0.3.0**  
added support links to UWP apps  

**0.2.1**  
released to PyPI  

**0.2.0**  
converted to python 3  
