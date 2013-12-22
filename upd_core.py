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


import re
import sys
import inspect
import os
import os.path
import collections
import logging
import zipfile
import tarfile
import json
import glob

import tempfile
import httplib
import ssl
from urlparse import urlparse
import shutil
import urllib2

import upd_version
from upd_iface import UpdateConsoleInterface
import upd_source


logger = logging.getLogger('updater4pyi')



class Updater4PyiError(Exception):
    def __init__(self, msg):
        self.updater_msg = msg
        Exception.__init__(self, 'Software Updater Error: '+msg);



# --------------------------------------------------------------------------------

_update_source = None
_update_interface = None

_current_version = None
_file_to_update = None


def get_update_source():
    return _update_source

def get_update_interface():
    return _update_interface

def current_version():
    return _current_version

def file_to_update():
    return _file_to_update


def setup_updater(current_version, update_source, update_interface=None):
    """
    Installs an update checker, implemented by the source `update_source` (a
    `upd_source.UpdateSource` subclass instance), and the user interface
    `update_interface` (itself an `upd_iface.UpdateInterface` subclass instance).

    The `current_version` is the current version string of the software, and will
    be provided to the `udpate_source`.
    """

    global _update_source
    global _update_interface
    global _current_version
    global _file_to_update

    # sys._MEIPASS seems to be set all the time, even we don't self-extract.
    if (not hasattr(sys, '_MEIPASS')):
        raise Updater4PyiError("This installation is not built with pyinstaller.")

    if (update_interface is None):
        update_interface = UpdateConsoleInterface()
    
    _update_source = update_source
    _update_interface = update_interface

    logger.debug("source is %r, interface is %r" %(_update_source, _update_interface))

    _current_version = current_version
    _file_to_update = determine_file_to_update()

    _update_interface.start()



# -------------------------------

CERT_FILE = os.path.join(os.path.dirname(__file__), 'root.pem');

class ValidHTTPSConnection(httplib.HTTPConnection):
    """
    HTTPS connection based on httplib.HTTPConnection, with certificate validation.
    """

    default_port = httplib.HTTPS_PORT

    def __init__(self, *args, **kwargs):
        httplib.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        """
        Connect to a host on a given (SSL) port.
        """
        
        sock = socket.create_connection((self.host, self.port),
                                        self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock,
                                    ca_certs=CERT_FILE,
                                    cert_reqs=ssl.CERT_REQUIRED)


class ValidHTTPSHandler(urllib2.HTTPSHandler):

    def https_open(self, req):
            return self.do_open(ValidHTTPSConnection, req)


url_opener = urllib2.build_opener(ValidHTTPSHandler)
url_opener.addheaders = [('User-agent', 'Updater4Pyi-SoftwareUpdater %s'%(upd_version.version_str))]



# --------------------------------



FileToUpdate = collections.namedtuple('FileToUpdate', ('fn', 'reltype', 'executable',));


def determine_file_to_update():
    """
    Returns a FileToUpdate(fn=.., reltype=.., executable=...) named tuple.
    """
    
    executable = sys.executable
    updatefile = os.path.realpath(sys.executable)
    reltype = None

    if (sys.platform.startswith('darwin')):
        logger.debug("platform is Mac OS X")
        # see if we are a Mac OS X bundle
        (alllastdir,fn) = os.path.split(sys.executable);
        (beforelastdir,lastdir) = os.path.split(alllastdir);

        if (lastdir == 'MacOS' and beforelastdir == 'Contents'):
            # we're in a Mac OS X bundle, so the actual "executable" should point to the .app file
            reltype = upd_source.RELTYPE_BUNDLE_ARCHIVE
            (updatefile,junk) = os.path.split(beforelastdir);
            logger.debug("We're a bundle")

    if reltype is None:
        # if we're not already a bundle, check whether we're a directory to update
        if (hasattr(sys, '_MEIPASS')):
            meipass = os.path.realpath(sys._MEIPASS);
            if (updatefile.startswith(meipass)):
                # pyinstaller files are installed directly: it's the dir we need to update
                reltype = upd_source.RELTYPE_ARCHIVE
                updatefile = meipass;

    if reltype is None:
        # otherwise, we're a self-contained executable.
        reltype = upd_source.RELTYPE_EXE


    logger.debug("got FileToUpdate(fn=%r, reltype=%d, executable=%s)",
                 updatefile, reltype, executable)

    return FileToUpdate(fn=updatefile, reltype=reltype, executable=executable)




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



# -------------------------------------------


def check_for_updates():
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

    global _update_source
    global _update_interface
    global _current_version
    global _file_to_update

    releases = _update_source.get_releases(newer_than_version=_current_version)

    logger.debug("releases=%r" %(releases))

    if (releases is None):
        logger.warning("Software Update Source returned a None release list!")
        return None

    wanted_reltype = _file_to_update.reltype
    
    # this is current version
    curver = parse_version(_current_version)

    # select the releases that match our criteria;
    # also sort the releases by version number.
    rel_w_parsedversion = [(r, parse_version(r.get_version())) for r in releases]
    releases2 = sorted([(rel, relparsedver)
                        for (rel, relparsedver) in rel_w_parsedversion
                        if (rel.get_reltype() == wanted_reltype and
                            rel.get_platform() == simple_platform() and
                            relparsedver > curver)
                        ],
                       key=lambda r2: r2[1],
                       reverse=True);

    if (releases2):
        # found release(s) which are strictly newer, and which satisfy our format requirements.
        return releases2[0][0]

    # no update found
    logger.debug("No update found.")
    return None









# ------------------------------------------


SPECIAL_ZIP_FILES = ('_updater4pyi_metainf.json',
                     '_METAINF',
                     )


def install_update(rel_info):

    # first, save the file locally.
    tmpfile = tempfile.NamedTemporaryFile(mode='w+b', prefix='upd4pyi_tmp_', dir=None, delete=False)

    url = rel_info.get_url();

    try:
        download_file(url, tmpfile)
    except IOError as e: 
        if hasattr(e, 'code'): # HTTPError 
            raise Updater4PyiError('Got HTTP error: %d %s' %(e.code, e.reason))
        elif hasattr(e, 'reason'): # URLError 
            raise Updater4PyiError('Connection error: %s' %(e.reason))
        else:
            raise Updater4PyiError('Error: %s' %(str(e)))

    # file is downloaded and on disk.

    # now, determine what we have to update on disk.
    filetoupdate = file_to_update()

    # TODO: add support for download verifyer (MD5/SHA or GPG signature)
    # ...

    # move that file out of the way, but keep it as backup. So just rename it.
    backupfilename = _backupname(filetoupdate.fn)
    try:
        os.rename(filetoupdate.fn, backupfilename);
    except OSError as e:
        raise Updater4PyiError("Failed to rename file %s!" %(str(e)))

    def restorebackup():
        try:
            shutil.rmtree(filetoupdate.fn)
            shutil.move(backupfilename, filetoupdate.fn)
        except OSError as e:
            logger.error("Software Update Error: Failed to restore backup %s of %s! %s\n"
                         % (backupfilename, filetoupdate.fn, str(e)))
            pass

    reltype_is_dir = filetoupdate.reltype in (upd_source.RELTYPE_BUNDLE_ARCHIVE,
                                              upd_source.RELTYPE_ARCHIVE);

    try:
        if (reltype_is_dir):
            # we are updating the directory itself. So make sure we download an archive file.

            (basedir, basefn) = os.path.split(filetoupdate.fn)

            def get_extract_to(namelist):
                extractto = None
                if ([True for x in namelist if not x.startswith(basefn) and x not in SPECIAL_ZIP_FILES]):
                    # the zip file doesn't extract into a single dir--there are files with different prefixes.
                    # so extract into a single dir ourselves.
                    try:
                        os.mkdir(filetoupdate.fn)
                    except OSError as e:
                        raise Updater4PyiError("Failed to create directory %s!" %(filetoupdate.fn))

                    extractto = filetoupdate.fn
                else:
                    extractto = basedir
                return extractto

            if (zipfile.is_zipfile(tmpfile.name)):
                # ZIP file
                thezipfile = zipfile.ZipFile(tmpfile.name, 'r')
                # extract the ZIP file to our directory.

                extractto = get_extract_to(thezipfile.namelist())

                permdata = None
                if ('_updater4pyi_metainf.json' in thezipfile.namelist()):
                    # adjust permissions on files.
                    try:
                        permdata = json.load(thezipfile.open('_updater4pyi_metainf.json'))
                    except ValueError as e:
                        logger.warning("Invalid JSON data in metainf file _updater4pyi_metainf.json: %s" %(str(e)))

                thezipfile.extractall(extractto, [x for x in thezipfile.namelist() if x not in SPECIAL_ZIP_FILES])
                thezipfile.close()

                if permdata and 'permissions' in permdata:
                    for (pattern,perm) in permdata['permissions'].iteritems():
                        logger.debug("pattern: %s to perms=%s" %(pattern, perm))
                        # int(s, 0) converts s to int, parsing prefixes '0' (octal), '0x' (hex)
                        # cf. http://stackoverflow.com/questions/604240/
                        iperm = int(perm,0);
                        for it in glob.iglob(os.path.join(filetoupdate.fn, pattern)):
                            logger.debug("Changing permissions of %s to %#o" %(it, iperm))
                            try:
                                os.chmod(it, iperm)
                            except OSError:
                                logger.warning("Failed to set permissions to file %s. Ignoring." %(it));
                                pass

                # remove the temporary downloaded file.
                os.unlink(tmpfile.name)
                
            elif tarfile.is_tarfile(tmpfile.name):
                # TAR[/GZ/BZIP2] file
                thetarfile = tarfile.open(tmpfile.name, 'r');
                # extract the ZIP file to our directory.

                extractto = get_extract_to(thetarfile.getnames())

                thezipfile.extractall(extractto)
                thezipfile.close()

                # remove the temporary downloaded file.
                os.unlink(tmpfile.name)

            else:
                raise Updater4PyiError("Downloaded file %s is not an archive." %(os.path.basename(tmpfile.name)))

        else:
            # following docs: these may be on different filesystems, and docs specify that os.rename()
            # may fail in that case. So use shutil.move() which should work.
            shutil.move(tmpfile.name, filetoupdate.fn)
            
            # make sure the file is executable
            os.chmod(filetoupdate.fn,
                     stat.S_IREAD|stat.S_IWRITE|stat.S_IEXEC|
                     stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|
                     stat.S_IRGRP|stat.S_IXGRP|
                     stat.S_IROTH|stat.S_IXOTH
                     )


    except:
        logger.error("Software Update Error: %s\n" %(str(sys.exc_info()[1])));
        restorebackup()
        raise

    logger.warning("For debugging & possible unstability, NOT removing backup.")
    # remove the backup.
    #if (reltype_is_dir):
    #    shutil.rmtree(backupfilename)
    #else
    #    os.unlink(backupfilename)
    
    

def _backupname(filename):
    try_suffix = '.bkp'
    n = 1
    while (n < 999 and os.path.exists(filename+try_suffix)):
        try_suffix = '.'+str(n)+'.bkp'
        n += 1;
    if (os.path.exists(filename+try_suffix)):
        raise Updater4PyiError("Can't figure out a backup name for file %s!!" %(filename))
    logger.debug("Got backup name: %s" %(filename+try_suffix))
    return filename+try_suffix;





def download_file(theurl, fdst):

    logger.debug("fetching URL %s to temp file %s ..." %(theurl, _noexcept(lambda : fdst.name)))

    fdata = url_opener.open(theurl);
    shutil.copyfileobj(fdata, fdst)
    fdata.close()
    fdst.close()

    logger.debug("... done.")



def _noexcept(f):
    try:
        return f()
    except:
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
