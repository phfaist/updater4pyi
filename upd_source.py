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
import re
import os
import os.path
import logging
import copy

import upd_core

logger = logging.getLogger('updater4pyi')



RELTYPE_UNKNOWN = 0
RELTYPE_EXE = 1
RELTYPE_ARCHIVE = 2
RELTYPE_BUNDLE_ARCHIVE = 3

class BinReleaseInfo(object):
    def __init__(self, version=None, filename=None, url=None,
                 reltype=RELTYPE_UNKNOWN,
                 platform=None,
                 **kwargs):

        if not version:
            raise ValueError("BinReleaseInfo(): Version may not be None!")

        self.version = version
        self.filename = filename
        self.url = url
        self.reltype = reltype
        self.platform = platform

        for k,v in kwargs.iteritems():
            setattr(self, k, v)


    def get_version(self):
        return self.version

    def get_filename(self):
        return self.filename

    def get_url(self):
        return self.url

    def get_reltype(self):
        return self.reltype

    def get_platform(self):
        return self.platform





class UpdateSource(object):
    """
    Base abstract class for an update source.

    Subclasses should reimplement `get_releases()`.
    """
    
    def __init__(self, *args, **kwargs):
        self.current_version = None
        self.file_to_update = None
        super(UpdateSource, self).__init__(*args, **kwargs)

    # subclasses need to reimplement:

    def get_releases(self, newer_than_version=None, **kwargs):
        """
        Should return a list of `BinReleaseInfo` of available releases. If `newer_than_version`
        argument is provided, then this function should ignore releases older or equal to the
        given argument.
        """
        raise NotImplementedError





#
# UpdateInfoFromNameRegexpStrategy(
#     (relpattern(r'-macosx-app\.zip$', reltype=RELTYPE_BUNDLE_ARCHIVE, platform='macosx'),
#      relpattern(r'-(?P<platform>linux|win|macosx)\.zip$', reltype=RELTYPE_ARCHIVE, platform='macosx'),
#      relpattern(r'-linux.bin$', reltype=RELTYPE_EXE, platform='linux'),
#      relpattern(r'-win32.exe$', reltype=RELTYPE_EXE, platform='win'),
#     ) )
#

class IgnoreArgument:
    pass

def _make_bin_release_info(m, lst):

    logger.debug("make_bin_release_info: lst=%r", lst)

    args = {}
    for k,v in lst:
        val = None
        try:
            val = v(m=m)
        except TypeError:
            val = v
        if (isinstance(val, IgnoreArgument)):
            continue
        args[k] = val

    logger.debug("make_bin_release_info: final args=%r", args)

    return BinReleaseInfo(**args)


def relpattern(re_pattern, reltype=RELTYPE_UNKNOWN, platform=None, **kwargs):
    # fix the values with default parameters
    return (re_pattern,
            (lambda m, filename, url, version=None,
             _fix_plat=platform, _fix_rtyp=reltype, _fix_kwargs=copy.deepcopy(kwargs), **innerkwargs:
             _make_bin_release_info(m,
                                    [('version',version)] +
                                    _fix_kwargs.items() +
                                    [('filename', filename),
                                     ('url', url),
                                     ('platform',_fix_plat),
                                     ('reltype',_fix_rtyp)] +
                                    innerkwargs.items()
                                    )
             )
            )


class ReleaseInfoFromNameStrategy(object):
    """
    Base class for a strategy to identify release details from a file name.

    Some sources need such a stategy, such as `UpdateLocalDirectorySource` and
    `UpdateGithubRelasesSource`.
    """
    def __init__(self, patterns, *args, **kwargs):
        self.patterns = patterns
        super(ReleaseInfoFromNameStrategy, self).__init__(*args, **kwargs)

    def get_release_info(self, filename, url, **kwargs):

        logger.debug("Trying to match filename %r to get info. kwargs=%r", filename, kwargs)
        
        for (pat,cal) in self.patterns:
            m = re.search(pat, filename)
            if m is None:
                continue

            return cal(m, filename, url, **kwargs)

        logger.warning("Can't identify info for release file named %s!" %(filename))
        return None
    

_default_naming_strategy = (
    relpattern(r'(?P<version>-[\w]+)?-macosx-app\.(tar(\.gz|\.bz(ip)?2?|\.Z)|tgz|tbz2?|zip)$',
               version=lambda m: m.group('version') if m.group('version') else IgnoreArgument(),
               platform='macosx', reltype=RELTYPE_BUNDLE_ARCHIVE),
    relpattern(r'(?P<version>-[\w]+)?-(?P<platform>macosx|linux|win)\.(tar(\.gz|\.bz(ip)?2?|\.Z)|tgz|tbz2?|zip)$',
               version=lambda m: m.group('version') if m.group('version') else IgnoreArgument(),
               platform=lambda m: m.group('platform'), reltype=RELTYPE_ARCHIVE),
    relpattern(r'(?P<version>-[\w]+)?-(?P<platform>macosx|linux|win)(\.(exe|bin|run))?$',
               version=lambda m: m.group('version') if m.group('version') else IgnoreArgument(),
               platform=lambda m: m.group('platform'), reltype=RELTYPE_EXE),
    )


class UpdateLocalDirectorySource(UpdateSource):
    """
    Updates will be searched for in a local directory. Used for debugging.
    """
    
    def __init__(self, source_directory, naming_strategy=None, *args, **kwargs):

        if (naming_strategy is None):
            naming_strategy = _default_naming_strategy
        if (not isinstance(naming_strategy, ReleaseInfoFromNameStrategy)):
            naming_strategy = ReleaseInfoFromNameStrategy(naming_strategy)

        self.naming_strategy = naming_strategy
        
        super(UpdateLocalDirectorySource, self).__init__(*args, **kwargs)
        self.source_directory = source_directory


    def get_releases(self, newer_than_version=None, **kwargs):
        
        versiondirs = sorted([ vdir for vdir in os.listdir(self.source_directory)
                               if os.path.isdir(os.path.join(self.source_directory, vdir))
                               ],
                             key=upd_core.parse_version,
                             reverse=True);

        newer_than_version_parsed = upd_core.parse_version(upd_core.current_version())

        file_to_update = upd_core.file_to_update()

        (fupdatedir, fupdatebasename) = os.path.split(file_to_update.fn)
        
        inf_list = []

        for ver in versiondirs:

            logger.debug("got version: %s" %(ver))
            
            if (newer_than_version_parsed is not None and
                upd_core.parse_version(ver) <= newer_than_version_parsed):
                # no update found.
                break

            base = os.path.join(self.source_directory, ver)

            logger.debug("version %s is newer; base dir: %s" %(ver, base))

            # list files in that directory.
            for fn in os.listdir(base):
                inf = self.naming_strategy.get_release_info(filename=fn,
                                                            url='file://'+os.path.join(base, fn),
                                                            version=ver,
                                                            )
                if inf is not None:
                    inf_list.append(inf)

        # debug: list found versions
        logger.debug("Found releases:\n"+
                     "\n".join(["\t* %s, %s (%r)" %(r.get_filename(), r.get_version(), r.__dict__)
                                for r in inf_list])
                     )
        
        # return the list of releases
        return inf_list
    












