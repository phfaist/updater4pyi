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



class UpdateInfo(object):
    def __init__(self, version=None, filename=None, url=None, #signature=None,
                 **kwargs):
        self.version = version
        self.filename = filename
        self.url = url
        #self.signature = signature
        for k,v in kwargs.iteritems():
            setattr(self, k, v)

    def get_version(self):
        return self.version

    def get_filename(self):
        return self.filename

    def get_url(self):
        return self.url

    #def get_signature(self):
    #    return self.signature;




class UpdateSource(object):
    """
    Base abstract class for an update source.

    Subclasses should reimplement `check_for_update()`.
    """
    
    def __init__(self, *args, **kwargs):
        self.current_version = None
        self.file_to_update = None

    def set_current_version(self, current_version):
        self.current_version = current_version

    def set_file_to_update(self, file_to_update):
        """
        This is a `upd_core.FileToUpdate` object instance.
        """
        self.file_to_update = file_to_update

    def is_macosx(self):
        return sys.platform.startswith('darwin')

    def is_win(self):
        return sys.platform.startswith('win')

    def is_linux(self):
        return sys.platform.startswith('linux')

    def simple_platform(self):
        if self.is_macosx():
            return 'macosx'
        elif self.is_win():
            return 'win'
        elif self.is_linux():
            return 'linux'
        else:
            return sys.platform

    # subclasses need to reimplement:

    def check_for_update(self):
        """
        Should return an `UpdateInfo` object if an update is available, or `None` if not.

        Note that `self.current_version` contains the current software version.
        """
        raise NotImplementedError




class UpdateLocalDirectorySource(UpdateSource):
    """
    Updates will be searched for in a local directory. Used for debugging.
    """
    
    def __init__(self, source_directory, *args, **kwargs):
        super(UpdateLocalDirectorySource, self).__init__(*args, **kwargs)
        self.source_directory = source_directory

    def check_for_update(self):
        """
        Will check in directory self.source_directory for updates. Files should be organized
        in subdirectories which should be version names, e.g.

        ::
          1.0/
            binary-macosx[.zip]
            binary-linux[.zip]
            binary-win[.exe|.zip]
          1.1/
            binary-macosx[.zip]
            binary-linux[.zip]
            binary-win[.exe|.zip]
          ...

        This updater source is mostly for debugging.
        """
        
        versiondirs = sorted([ vdir for vdir in os.listdir(self.source_directory)
                               if os.path.isdir(os.path.join(self.source_directory, vdir))
                               ],
                             key=parse_version,
                             reverse=True);

        curver = parse_version(self.current_version);
        
        for ver in versiondirs:

            if (parse_version(ver) <= curver):
                # no update found.
                return None

            base = os.path.join(self.source_directory, newestversion)

            if (self.file_to_update.is_dir):
                zipfullfn = os.path.realpath(os.path.join(base,
                                                          self.file_to_update.fn + '-' +
                                                          self.simple_platform() + '.zip'));
                if (os.path.isfile(zipfullfn)):
                    return UpdateInfo(version=ver, filename=zipfullfn,
                                      url='file://'+zipfullfn)
                else:
                    print "Version %s does not provide zip file." %(ver)
                    # no zip file available for this version
                    continue

            # else: we're not a dir.

            matches = [ x for x in os.listdir(os.path.join(self.source_directory, ver))
                        if self.simple_platform() in x ]

            if (matches):
                return UpdateInfo(version=ver, filename=matches[0],
                                  url='file://'+os.path.join(self.source_directory, ver, matches[0]))

            # continue.
        
        # no update found
        print "No update found."
        return None


















# ------------------------------------------------------------------------

# Code taken from setuptools project,
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
