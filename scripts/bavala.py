"""
Copyright (C) 2012, 2013, 2014 Eduardo Naufel Schettino and Johan Mattsson

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

"""bavala is a build-tool for Vala that uses doit (http://pydoit.org)"""

import glob
import os
import sys
from os.path import join
from doit.action import CmdAction

try:
    import scripts.config as config
except ImportError:
    import config

import fnmatch
import subprocess

def cmd(name, *args):
    """create string for command line"""
    parts = [name]
    
    try:
        base = basestring
    except NameError:
        base = str

    for item in args:
        if isinstance(item, base):
            parts.append(item)
        elif isinstance(item, dict):
            for param, value in item.items():
                if isinstance(value, base):
                    value = [value]
                parts.extend('--{0} {1}'.format(param, v) for v in value)
        else:
            parts.extend(item)

    cmd_parts = [] 
    for p in parts:
        if isinstance(p, str):
            cmd_parts += [p]
        else:
            cmd_parts += [p.decode("utf-8")]

    return ' '.join(cmd_parts)

def get_sources_path (folder, pattern):
    """obtain the path to all source files that matches pattern"""
    files = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, pattern):
            files.append(os.path.join(root, filename))
    return files



def get_sources_name (folder, pattern):
    """obtain name of all source files that matches pattern"""
    files = []
    for root, dirnames, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, pattern):
            files.append(filename)
    return files



class Vala(object):
    """helper to generate tasks to compile vala code"""

    def __init__(self, src, build, pkg_libs, library=None, vala_deps=None, so_version=None):
        self.src = src
        self.build = build
        self.pkg_libs = pkg_libs
        self.vala_deps = vala_deps or []
        self.library = library
		
        self.vala = get_sources_path (src, '*.vala')
        self.c = get_sources_path (src, '*.c') # copy regular c sources
        self.c += get_sources_path (src, '*.h') # copy header files for the c sources
        self.cc = [join(build + '/' + src, f) for f in get_sources_name (src, '*.c') ]
        self.cc += [join(build + '/' + src, f.replace('.vala', '.c')) for f in get_sources_name (src, '*.vala')]
        self.obj = [self.build + '/' + self.src + '/' + f.replace('.c', '.o') for f in get_sources_name (src, '*.c')]
        self.obj += [self.build + '/' + self.src + '/' +  f.replace('.vala', '.o') for f in get_sources_name (src, '*.vala')]
        
        if library:
            self.header = join(build, library) + '.h'
            self.vapi = join(build, library) + '.vapi' # generated vapi file
            self.other_vapi_files = get_sources_path (src, '*.vapi') # other vapi files
            self.so = join(build, src) + '.so.' + so_version
            self.so_link = join(build, src) + '.so'
            self.so_link_name = src + '.so'
            self.so_version = so_version
            self.so_name = 'lib' + library + '.so.' + so_version
        else:
            self.other_vapi_files = []

    def gen_c(self, opts):
        """translate code from vala to C and create .vapi"""
        options = ['--ccode']
        options.extend(opts)
        params = {
            'basedir': join(self.build, self.src),
            'vapidir': './',
            'pkg': self.pkg_libs,
            }
        if self.library:
            params['library'] = self.library
            params['vapi'] = self.vapi
            params['header'] = self.header

        dep_vapi = [d.vapi for d in self.vala_deps]
        action = cmd('valac', options, params, dep_vapi, self.vala)
        targets = self.cc[:]
        
        if self.library:
            targets += [self.header, self.vapi]
       
        for f in self.c:
            yield {
                'name': 'copy_c_' + f,
                'actions': [ 
                    'mkdir -p '+  self.build + '/' + self.src + '/', 
                    'cp ' + f + ' ' + self.build + '/' + self.src + '/'
                    ],
                }
 
        for f in self.other_vapi_files:
            yield {
                'name': 'vapi_files_' + f,
                'actions': [ 
                    'mkdir -p '+  self.build + '/', 
                    'cp ' + f + ' ' + self.build + '/'
                    ],
                }
        
        print (action)
        
        if not self.vala == []:
            yield {
                'name': 'compile_c',
                'actions': [ action ],
                'file_dep': self.vala + dep_vapi,
                'targets': targets,
            }


    def gen_o(self, opts):
        """compile C files to obj `.o` """
        def compile_cmd(conf, opts, libs, pos):
            flags = []
            for l in libs:
                if not l == "posix" and not l == "posixtypes":
                    process = subprocess.Popen ('pkg-config --cflags ' + l, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    cflags = process.stdout.readline()
                    process.communicate()[0]
                    if not process.returncode == 0:
                        print ( "Library not found: " + l)
                        exit (1)
                    flags += [cflags.strip ()]

            return cmd(config.CC, opts, flags, pos)

        for cc, obj in zip(self.cc, self.obj):
            pos = ["-c " + cc, "-o " + obj ]
            cmd_args = {'libs':self.pkg_libs, 'opts':opts, 'pos':pos}
            action = CmdAction((compile_cmd, [], cmd_args))
            
            yield {
                'name': obj.rsplit('/')[-1],
                'file_dep': [ cc ],
                'actions': [ action ],
                'getargs': { 'conf': ('pkg_flags', 'out') },
                'targets': [ obj ],
                }


    def gen_so(self, generated_libs = None):
        """generate ".so" lib file"""
        def compile_cmd(conf, libs):
            obj_glob = join(self.build, self.src, '*.o')
            opts = ['-shared ' 
                    + '-Wl,-soname,' + self.so_name 
			        + ' ' + obj_glob
                    + ' -o ' + self.so ]

            flags = []
            for l in libs:
                if not l == "posix" and not l == "posixtypes":
                    process = subprocess.Popen ('pkg-config --cflags ' + l, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    cflags = process.stdout.readline()
                    process.communicate()[0]
                    if not process.returncode == 0:
                        print ( "Library not found: " + l)
                        exit (1)
                    flags += [cflags.strip ()]

            if generated_libs:
                flags += [generated_libs]
			    
            return cmd(config.CC, opts, flags)

        return {
            'name': self.so.rsplit('/')[-1],
            'actions': [ CmdAction((compile_cmd, [], {'libs':self.pkg_libs})) ],
            'getargs': { 'conf': ('pkg_flags', 'out') },
            'file_dep': self.obj,
            'targets': [ self.so ],
            }

    def gen_ln(self):
        """generate a symbolic link to the generated ".so" file"""
        so_file = self.so.rsplit('/')[-1]
        
        if "kfreebsd" in sys.platform:
            create_link = "ln -s -T " + so_file + " " + self.so_link_name + " "
        elif not "bsd" in sys.platform:
            create_link = "ln -s -T " + so_file + " " + self.so_link_name + " "

        create_link += "&& mv " + self.so_link_name + " " + self.build + "/" 
        return {
            'name': self.so_link_name,
            'actions': [ create_link],
            'file_dep': [ self.so ],
            'targets': [ self.so_link ],
            }

    def gen_bin(self, opts):
        """generate binary"""
        def compile_cmd(conf, opts, libs):
            flags = [conf[l].strip() for l in libs]
            return cmd(config.CC, opts, flags)

        bin_path = join(self.build, 'bin')
        target = join(bin_path, self.src)
        opts = (self.cc + opts +
                ['-o ' + target, '-I ' + self.build, '-L ' + self.build] +
                ['-l ' + d.library for d in self.vala_deps])
        action = CmdAction((compile_cmd, [], {'opts':opts, 'libs':self.pkg_libs}))
        yield {
            'name': "bin",
            'actions': [ 'mkdir -p %s' % bin_path, action ],
            'getargs': { 'conf': ('pkg_flags', 'out') },
            'file_dep': self.cc + [ d.so_link for d in self.vala_deps ],
            'targets': [ target ],
            }




