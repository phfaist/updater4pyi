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
import json
import inspect
import urllib2

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

    def __repr__(self):
        return (self.__class__.__name__+'('+
                ", ".join([ '%s=%r' % (k,v)
                            for (k,v) in self.__dict__.iteritems() ]) +
                ')')




# --------------------------------------------------------------



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





# ---------------------------------------------------------------------------

class IgnoreArgument:
    pass

def _make_bin_release_info(m, lst, innerkwargs):

    logger.debug("make_bin_release_info: lst=%r", lst)

    args = {}
    for k,v in lst+innerkwargs.items():
        val = None
        if (type(v).__name__ == 'function'):
            argspec = inspect.getargspec(v)
            valargs = {}
            if ('m' in argspec.args or argspec.keywords is not None):
                valargs['m'] = m;
            if ('d' in argspec.args or argspec.keywords is not None):
                valargs['d'] = innerkwargs;

            val = v(**valargs)
        else:
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
                                    [ ('version',version) ] +
                                    _fix_kwargs.items() +
                                    [ ('filename', filename),
                                      ('url', url),
                                      ('platform',_fix_plat),
                                      ('reltype',_fix_rtyp) ],
                                    innerkwargs
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
        self.patterns = [(_maybe_compile_re(r), cal) for (r, cal) in patterns]
        super(ReleaseInfoFromNameStrategy, self).__init__(*args, **kwargs)

    def get_release_info(self, filename, url, **kwargs):

        logger.debug("Trying to match filename %r to get info. kwargs=%r", filename, kwargs)
        
        for (pat,cal) in self.patterns:
            m = re.search(pat, filename)
            if m is None:
                continue

            rinfo = cal(m, filename, url, **kwargs)
            logger.debug("Got release info: %r", rinfo)
            return rinfo

        logger.warning("Can't identify info for release file named %s!" %(filename))
        return None

def _maybe_compile_re(r, flags=re.IGNORECASE):
    if (isinstance(r, type(re.compile('')))):
        return r
    return re.compile(r, flags)


_RX_VER = r'(-(?P<version>[\w]+))?'
_RX_PLAT = r'-(?P<platform>macosx|linux|win)'

_default_naming_strategy_patterns = (
    relpattern(_RX_VER+r'-macosx\.(tar(\.gz|\.bz(ip)?2?|\.Z)|tgz|tbz2?|zip)$',
               version=lambda m: m.group('version') if m.group('version') else IgnoreArgument(),
               platform='macosx', reltype=RELTYPE_BUNDLE_ARCHIVE),
    relpattern(_RX_VER+_RX_PLAT+r'(-onedir)?\.(tar(\.gz|\.bz(ip)?2?|\.Z)|tgz|tbz2?|zip)$',
               version=lambda m: m.group('version') if m.group('version') else IgnoreArgument(),
               platform=lambda m: m.group('platform').lower(), reltype=RELTYPE_ARCHIVE),
    relpattern(_RX_VER+_RX_PLAT+r'(\.(exe|bin|run))?$',
               version=lambda m: m.group('version') if m.group('version') else IgnoreArgument(),
               platform=lambda m: m.group('platform').lower(), reltype=RELTYPE_EXE),
    )

# maybe e.g.
# UpdateInfoFromNameRegexpStrategy(
#     (relpattern(r'-macosx-app\.zip$', reltype=RELTYPE_BUNDLE_ARCHIVE, platform='macosx'),
#      relpattern(r'-(?P<platform>linux|win|macosx)\.zip$', reltype=RELTYPE_ARCHIVE, platform='macosx'),
#      relpattern(r'-linux.bin$', reltype=RELTYPE_EXE, platform='linux'),
#      relpattern(r'-win32.exe$', reltype=RELTYPE_EXE, platform='win'),
#     ) )
#








# -------------------------------------------------------


class UpdateLocalDirectorySource(UpdateSource):
    """
    Updates will be searched for in a local directory. Used for debugging.
    """
    
    def __init__(self, source_directory, naming_strategy=None, *args, **kwargs):

        if (naming_strategy is None):
            naming_strategy = _default_naming_strategy_patterns
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
    







# -----------------------------------------------------------------


# github releases source



class UpdateGithubReleasesSource(UpdateSource):
    """
    Updates will be searched for in as releases of a github repo.
    """
    
    def __init__(self, github_user_repo, naming_strategy=None, *args, **kwargs):
        """
        `github_user_repo` is a string literal `'user/repo_name'`, e.g. `'phfaist/bibolamazi'`.
        """

        if (naming_strategy is None):
            naming_strategy = _default_naming_strategy_patterns
        if (not isinstance(naming_strategy, ReleaseInfoFromNameStrategy)):
            naming_strategy = ReleaseInfoFromNameStrategy(naming_strategy)

        self.naming_strategy = naming_strategy
        self.github_user_repo = github_user_repo

        super(UpdateGithubReleasesSource, self).__init__(*args, **kwargs)


    def get_releases(self, newer_than_version=None, **kwargs):

        # get repo releases.

        url = 'https://api.github.com/repos/'+self.github_user_repo+'/releases'

        try:
            fdata = upd_core.url_opener.open(url)
        except urllib2.URLError:
            logger.warning("Can't connect to github for software update check.")
            return None

        try:
            data = json.load(fdata);
        except ValueError:
            logger.warning("Unable to parse data returned by github at %s!", url)
            return None

        if (isinstance(data, dict)):
            logger.warning("Error: %s" %(data.get('message', '<no message provided>')))
            return None

        if (not isinstance(data, list)):
            logger.warning("Expected list response from github: %r", data)
            return None

        newer_than_version_parsed = None
        if (newer_than_version is not None):
            newer_than_version_parsed = upd_core.parse_version(newer_than_version)

        inf_list = []
        
        for relinfo in data:
            html_url = relinfo.get('html_url', None)
            tag_name = relinfo.get('tag_name', None)
            rel_name = relinfo.get('name', '<unknown>')
            rel_desc = relinfo.get('body', None)
            rel_date = relinfo.get('published_at', None)
            
            # release version from tag name
            # strip starting 'v' if present
            relver = '0.0-unknown'
            if tag_name:
                relver = (tag_name[1:] if tag_name[0] == 'v' else tag_name)

            if (newer_than_version_parsed is not None and
                upd_core.parse_version(relver) <= newer_than_version_parsed):
                logger.debug("Version %s is not strictly newer than %s, skipping...", relver, newer_than_version)
                continue
                
            relfiles = relinfo.get('assets', {})
            for relfile in relfiles:

                relfn = relfile.get('name', None)
                rellabel = relfile.get('label', None)
                relcontenttype = relfile.get('content_type', None)
                # build up the download URL
                relurl = 'https://github.com/'+self.github_user_repo+'/releases/download/'+tag_name+'/'+relfn;

                inf_list.append(
                    self.naming_strategy.get_release_info(filename=relfn,
                                                          url=relurl,
                                                          version=relver,
                                                          # additional info:
                                                          rel_name=rel_name,
                                                          relfile_label=rellabel,
                                                          rel_description=rel_desc,
                                                          relfile_content_type=relcontenttype,
                                                          rel_tag_name=tag_name,
                                                          rel_html_url=html_url,
                                                          )
                    )

        # debug: list found versions
        logger.debug("Found releases:\n"+
                     "\n".join(["\t* %s, %s (%r)" %(r.get_filename(), r.get_version(), r.__dict__)
                                for r in inf_list])
                     )
        
        # return the list of releases
        return inf_list
    






