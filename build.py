#!/usr/bin/python3

import dodo
from sys import platform

from scripts.builder import process_tasks
from scripts import config
from scripts import version

if platform == 'msys':
	process_tasks(dodo.make_libxmlbird('libbirdgems.dll', []))
elif platform == 'darwin':
	lib = "libxmlbird." + str(version.LIBXMLBIRD_SO_VERSION_MAJOR) + '.dylib'
	process_tasks(dodo.make_libxmlbird(lib, []))
elif "openbsd" in platform:
    process_tasks(dodo.make_libxmlbird('libxmlbird.so.${LIBxmlbird_VERSION}'))
else:
	process_tasks(dodo.make_libxmlbird('libxmlbird.so'))
	
print('Done')