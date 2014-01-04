# -*- coding: utf-8 -*-
#######################################################################################
#                                                                                     #
#   This file is part of the updater4pyi Project.                                     #
#                                                                                     #
#   Copyright (C) 2013, Philippe Faist                                                #
#   philippe.faist@bluewin.ch                                                         #
#   All rights reserved.                                                              #
#                                                                                     #
#   Redistribution and use in source and binary forms, with or without                #
#   modification, are permitted provided that the following conditions are met:       #
#                                                                                     #
#   1. Redistributions of source code must retain the above copyright notice, this    #
#      list of conditions and the following disclaimer.                               #
#   2. Redistributions in binary form must reproduce the above copyright notice,      #
#      this list of conditions and the following disclaimer in the documentation      #
#      and/or other materials provided with the distribution.                         #
#                                                                                     #
#   THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND   #
#   ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED     #
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE            #
#   DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR   #
#   ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES    #
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;      #
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND       #
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT        #
#   (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS     #
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.                      #
#                                                                                     #
#######################################################################################

import sys
import os
import os.path
import re
import subprocess
import logging
import inspect

logger = logging.getLogger('updater4pyi')




# ------------------------------------

# platform utils


def is_macosx():
    return sys.platform.startswith('darwin')

def is_win():
    return sys.platform.startswith('win')

def is_linux():
    return sys.platform.startswith('linux')

def simple_platform():
    if is_macosx():
        return 'macosx'
    elif is_win():
        return 'win'
    elif is_linux():
        return 'linux'
    else:
        return sys.platform





# other utilities


def bash_quote(x):
    return "'" + x.replace("'", "'\\''") + "'"
def winshell_quote(x):
    # wait a minute, how are win/dos batch escapes ??!?
    # ... see http://technet.microsoft.com/en-us/library/cc723564.aspx
    return '"' + x.replace('"', '""') + '"'
def applescript_quote(x):
    return '"' + re.sub(r'([\\"])', r'\\\1', x) + '"'


# ------------------------------------------------------------------------

# utility to get resource files bundled with pyinstaller

def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller
    """
    def base_path():
        try:
            return sys._MEIPASS
        except AttributeError:
            pass
        mainfn = inspect.stack()[-1][1]
        return os.path.abspath(os.path.dirname(mainfn))

    return os.path.join(base_path(), relative_path)


# ------------


def run_as_admin(argv):
    cmd = [];
    if is_macosx():
        cmd = ["osascript",
               "-e",
               "do shell script " + applescript_quote(
                   " ".join([bash_quote(x) for x in argv])
                   ) + " with administrator privileges"
               ]
    elif is_linux():
        # repeated use of which() is ok because it caches result
        if which('pkexec'):
            cmd = [which('pkexec')] + argv
        elif which('gksudo'):
            cmd = [which('gksudo')] + argv
        elif which('kdesudo'):
            cmd = [which('kdesudo')] + argv
        elif os.environ.get('DISPLAY') and which('xterm'):
            cmd = [which('xterm'), '-e', 'sudo'] + argv
        else:
            cmd = [which('sudo')] + argv
    elif is_win():
        # our helper function
        return _run_as_admin_win(argv);
    else:
        logger.error("Platform not recognized for running process as admin: %s",
                     simple_platform())
        raise NotImplementedError

    logger.debug("Running command %r", cmd)

    # run the prepared command
    retcode = subprocess.call(cmd, stdin=None, stdout=None, stderr=None,
                              shell=False)
    if (retcode != 0):
        # produce a warning in case of an error.
        logger.warning("admin subprocess %s failed", (argv[0] if argv else None))

    return retcode


# -----------------------------------------------------------------------------------
#
# code inspired from http://stackoverflow.com/a/19719292/1694896
#
def _run_as_admin_win(argv, wait=True):

    if os.name != 'nt':
        raise RuntimeError, "This function is only implemented on Windows."

    import win32api, win32con, win32event, win32process
    from win32com.shell.shell import ShellExecuteEx
    from win32com.shell import shellcon

    cmd = winshell_quote(argv[0])
    # XXX TODO: isn't there a function or something we can call to massage command line params?
    params = " ".join([winshell_quote(x) for x in argv[1:]])
    
    cmdDir = ''
    showCmd = win32con.SW_SHOWNORMAL
    #showCmd = win32con.SW_HIDE
    lpVerb = 'runas'  # causes UAC elevation prompt.

    logger.debug("running %s %s", cmd, params)

    # ShellExecute() doesn't seem to allow us to fetch the PID or handle
    # of the process, so we can't get anything useful from it. Therefore
    # the more complex ShellExecuteEx() must be used.

    # procHandle = win32api.ShellExecute(0, lpVerb, cmd, params, cmdDir, showCmd)

    procInfo = ShellExecuteEx(nShow=showCmd,
                              fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
                              lpVerb=lpVerb,
                              lpFile=cmd,
                              lpParameters=params)

    if wait:
        procHandle = procInfo['hProcess']    
        obj = win32event.WaitForSingleObject(procHandle, win32event.INFINITE)
        rc = win32process.GetExitCodeProcess(procHandle)
        logger.debug("Process handle %s returned code %s", (procHandle, rc))
    else:
        rc = None

    return rc








# --------------------------------------------------------------------------------------------

# Code for parse_version() taken from setuptools project,
#
# https://bitbucket.org/pypa/setuptools/src/353a4270074435faa7daa2aa0ee480e22e505f53/pkg_resources.py?at=default
#
# TODO: didn't find license information. Is there any?
#

_component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
_replace = {'pre':'c', 'preview':'c','-':'final-','rc':'c','dev':'@'}.get

def _parse_version_parts(s):
    for part in _component_re.split(s):
        part = _replace(part,part)
        if not part or part=='.':
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        else:
            yield '*'+part

    yield '*final'  # ensure that alpha/beta/candidate are before final

def parse_version(s):
    """Convert a version string to a chronologically-sortable key

    This is a rough cross between distutils' StrictVersion and LooseVersion;
    if you give it versions that would work with StrictVersion, then it behaves
    the same; otherwise it acts like a slightly-smarter LooseVersion. It is
    *possible* to create pathological version coding schemes that will fool
    this parser, but they should be very rare in practice.

    The returned value will be a tuple of strings.  Numeric portions of the
    version are padded to 8 digits so they will compare numerically, but
    without relying on how numbers compare relative to strings.  Dots are
    dropped, but dashes are retained.  Trailing zeros between alpha segments
    or dashes are suppressed, so that e.g. "2.4.0" is considered the same as
    "2.4". Alphanumeric parts are lower-cased.

    The algorithm assumes that strings like "-" and any alpha string that
    alphabetically follows "final"  represents a "patch level".  So, "2.4-1"
    is assumed to be a branch or patch of "2.4", and therefore "2.4.1" is
    considered newer than "2.4-1", which in turn is newer than "2.4".

    Strings like "a", "b", "c", "alpha", "beta", "candidate" and so on (that
    come before "final" alphabetically) are assumed to be pre-release versions,
    so that the version "2.4" is considered newer than "2.4a1".

    Finally, to handle miscellaneous cases, the strings "pre", "preview", and
    "rc" are treated as if they were "c", i.e. as though they were release
    candidates, and therefore are not as new as a version string that does not
    contain them, and "dev" is replaced with an '@' so that it sorts lower than
    than any other pre-release tag.
    """
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            if part<'*final':   # remove '-' before a prerelease tag
                while parts and parts[-1]=='*final-': parts.pop()
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1]=='00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)





# --------------------------------------------------------------------------------------------

# function which() is based on code from
# http://twistedmatrix.com/trac/browser/tags/releases/twisted-8.2.0/twisted/python/procutils.py
#
# license notice:
#
# Copyright (c) 2001-2008
# Allen Short
# Andrew Bennetts
# Apple Computer, Inc.
# Benjamin Bruheim
# Bob Ippolito
# Canonical Limited
# Christopher Armstrong
# David Reid
# Donovan Preston
# Eric Mangold
# Itamar Shtull-Trauring
# James Knight
# Jason A. Mobarak
# Jean-Paul Calderone
# Jonathan Lange
# Jonathan D. Simms
# Jürgen Hermann
# Kevin Turner
# Mary Gardiner
# Matthew Lefkowitz
# Massachusetts Institute of Technology
# Moshe Zadka
# Paul Swartz
# Pavel Pergamenshchik
# Ralph Meijer
# Sean Riley
# Software Freedom Conservancy
# Travis B. Hartwell
# Thomas Herve
# Eyal Lotem
# Antoine Pitrou
# Andy Gayton
# 
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

# ### PhF: cache which() results
_which_cache = {}
_which_cache_first = {}

def which_clear_cache():
    _which_cache.clear()
    _which_cache_first.clear()

def which(name, flags=os.X_OK, usecache=True, firstresult=True):
    """Search PATH for executable files with the given name.

    On newer versions of MS-Windows, the PATHEXT environment variable will be
    set to the list of file extensions for files considered executable. This
    will normally include things like ".EXE". This fuction will also find files
    with the given name ending with any of these extensions.

    On MS-Windows the only flag that has any meaning is os.F_OK. Any other
    flags will be ignored.

    @type name: C{str}
    @param name: The name for which to search.

    @type flags: C{int}
    @param flags: Arguments to L{os.access}.

    @rtype: C{list}
    @param: A list of the full paths to files found, in the
    order in which they were found.
    """

    # PhF: check in the cache first, see if we've found `name` already
    if (usecache):
        if firstresult:
            if name in _which_cache_first:
                return _which_cache_first.get(name)
        else:
            if name in _which_cache:
                return _which_cache.get(name)

    result = []
    exts = filter(None, os.environ.get('PATHEXT', '').split(os.pathsep))
    path = os.environ.get('PATH', None)
    if path is None:
        return []
    for p in os.environ.get('PATH', '').split(os.pathsep):
        p = os.path.join(p, name)
        if os.access(p, flags):
            result.append(p)
        for e in exts:
            pext = p + e
            if os.access(pext, flags):
                result.append(pext)
        if (firstresult and result):
            # we've found a result, return it
            _which_cache_first[name] = result[0]
            return result[0]
        
    if usecache and result:
        # we know that firstresult=False because otherwise we would have
        # returned already.
        _which_cache[name] = result

    return result
