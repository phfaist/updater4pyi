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
import stat
import collections
import logging
import zipfile
import tarfile
import json
import glob
import subprocess

import tempfile
import httplib
import ssl
import socket
from urlparse import urlparse
import shutil
import urllib2

from . import util
from . import upd_version


logger = logging.getLogger('updater4pyi')



class Updater4PyiError(Exception):
    def __init__(self, msg):
        self.updater_msg = msg
        Exception.__init__(self, 'Software Updater Error: '+msg);


# ------------------------------------------------------------------------

# release package types


RELTYPE_UNKNOWN = 0
RELTYPE_EXE = 1
RELTYPE_ARCHIVE = 2
RELTYPE_BUNDLE_ARCHIVE = 3



# ------------------------------------------------------------------------

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
        from .upd_iface import UpdateConsoleInterface
        update_interface = UpdateConsoleInterface()
    
    _update_source = update_source
    _update_interface = update_interface

    logger.debug("source is %r, interface is %r" %(_update_source, _update_interface))

    _current_version = current_version
    _file_to_update = determine_file_to_update()

    _update_interface.start()



# -------------------------------

CERT_FILE = util.resource_path('updater4pyi/cacert.pem');#'root.crt');

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

        logger.debug("Connecting via HTTPS to %s:%d.", self.host, self.port)
        
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

    logger.debug("trying to determine pyi executable to update. sys.executable=%s; sys._MEIPASS=%s",
                 sys.executable, (sys._MEIPASS if hasattr(sys, '_MEIPASS') else '<no sys._MEIPASS>'))

    if (sys.platform.startswith('darwin')):
        # see if we are a Mac OS X bundle
        (alllastdir,fn) = os.path.split(sys.executable);
        (allbeforelastdir,lastdir) = os.path.split(alllastdir);
        (allbeforebeforelastdir,beforelastdir) = os.path.split(allbeforelastdir);

        logger.debug("platform is Mac OS X; alllastdir=%s, beforelastdir=%s, lastdir=%s, fn=%s",
                     alllastdir, beforelastdir, lastdir, fn)

        if (lastdir == 'MacOS' and beforelastdir == 'Contents'):
            # we're in a Mac OS X bundle, so the actual "executable" should point to the .app file
            reltype = RELTYPE_BUNDLE_ARCHIVE
            updatefile = allbeforebeforelastdir
            logger.debug("We're a bundle: updatefile=%s", updatefile)

    if reltype is None:
        # if we're not already a bundle, check whether we're a directory to update
        if (hasattr(sys, '_MEIPASS')):
            meipass = os.path.realpath(sys._MEIPASS);
            if (updatefile.startswith(meipass)):
                # pyinstaller files are installed directly: it's the dir we need to update
                reltype = RELTYPE_ARCHIVE
                updatefile = meipass;

    if reltype is None:
        # otherwise, we're a self-contained executable.
        reltype = RELTYPE_EXE


    logger.debug("got FileToUpdate(fn=%r, reltype=%d, executable=%s)",
                 updatefile, reltype, executable)

    return FileToUpdate(fn=updatefile, reltype=reltype, executable=executable)





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
    curver = util.parse_version(_current_version)

    # select the releases that match our criteria;
    # also sort the releases by version number.
    rel_w_parsedversion = [(r, util.parse_version(r.get_version())) for r in releases]
    releases2 = sorted([(rel, relparsedver)
                        for (rel, relparsedver) in rel_w_parsedversion
                        if (rel.get_reltype() == wanted_reltype and
                            rel.get_platform() == util.simple_platform() and
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

class _ExtractLocation(object):
    def __init__(self, filetoupdate, needs_sudo, **kwargs):
        self.filetoupdate = filetoupdate
        self.needs_sudo = needs_sudo

        super(_ExtractLocation, self).__init__(**kwargs)


    def findextractto(self, namelist):
        
        (basedir, basefn) = os.path.split(self.filetoupdate.fn)

        self.extractto = None
        self.installto = None
        self.extracttotemp = False

        self.extractstodir = True
        if ([True for x in namelist if not x.startswith(basefn) and x not in SPECIAL_ZIP_FILES]):
            # the zip file doesn't extract into a single dir--there are files with different prefixes.
            # so extract into a single dir ourselves.
            self.extractstodir = False
            self.extractto = self.filetoupdate.fn
            if not self.needs_sudo:
                # create the directory only if we don't need superuser rights for installation
                try:
                    os.mkdir(self.filetoupdate.fn)
                except OSError as e:
                    raise Updater4PyiError("Failed to create directory %s!" %(self.filetoupdate.fn))
        else:
            self.extractto = basedir

        if self.needs_sudo:
            # in any case, if we need superuser rights for installation, then extract
            # to a temporary directory.
            self.installto = self.extractto
            self.extracttotemp = True
            # NOTE: Don't change prefix and suffix, this name template is relied upon by do_install.exe !!
            self.extractto = tempfile.mkdtemp(suffix='', prefix='upd4pyi_tmp_xtract_', dir=None)

        return self.extractto


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

    # detect if admin rights are needed.
    if not util.is_win():
        needs_sudo = not os.access(filetoupdate.fn, os.W_OK);
    else:
        needs_sudo = True
        try:
            with open(filetoupdate.executable, 'r+') as f:
                pass
            needs_sudo = False
        except OSError:
            # the file is write-protected
            needs_sudo = True

    # ###FIXME: os.access() does not work as expected on windows. Solution: try
    #           open(filetoupdate.executable, 'r+') in a `try / except OSError` block?


    

    # determine if we will work in the temporary dir only and call an external utility (e.g. do_install.exe)
    # or if we will directly unpack e.g. the zip file at the right location.
    #
    # reasons for staying in temp locations are:
    #   * final location requires root access
    #   * windows: can't overwrite files of the running process.
    needs_work_in_temp_dir = needs_sudo or util.is_win();

    logger.debug("installation will need sudo? %s", needs_sudo)

    # move that file out of the way, but keep it as backup. So just rename it.
    backupfilename = _backupname(filetoupdate.fn)
    if not needs_work_in_temp_dir:
        try:
            os.rename(filetoupdate.fn, backupfilename);
        except OSError as e:
            raise Updater4PyiError("Failed to rename file %s!" %(str(e)))

    def restorebackup():
        if needs_work_in_temp_dir:
            # no backup was generated anyway at this point
            return
        try:
            shutil.rmtree(filetoupdate.fn)
        except OSError:
            # ignore
            pass
        try:
            shutil.move(backupfilename, filetoupdate.fn)
        except OSError as e:
            logger.error("Software Update Error: Failed to restore backup %s of %s! %s\n"
                         % (backupfilename, filetoupdate.fn, str(e)))
            pass

    reltype_is_dir = filetoupdate.reltype in (RELTYPE_BUNDLE_ARCHIVE,
                                              RELTYPE_ARCHIVE);

    extractedfile = None
    installto = None

    try:
        if (reltype_is_dir):
            # we are updating the directory itself. So make sure we download an archive file.

            extractloc = _ExtractLocation(filetoupdate=filetoupdate,
                                          needs_sudo=needs_work_in_temp_dir)

            logger.debug("extractloc: %r", extractloc.__dict__)

            if (zipfile.is_zipfile(tmpfile.name)):
                # ZIP file
                thezipfile = zipfile.ZipFile(tmpfile.name, 'r')
                
                # extract the ZIP file to our directory.

                extractloc.findextractto(namelist=thezipfile.namelist())
                extractto = extractloc.extractto

                permdata = None
                if ('_updater4pyi_metainf.json' in thezipfile.namelist()):
                    # adjust permissions on files.
                    try:
                        permdata = json.load(thezipfile.open('_updater4pyi_metainf.json'))
                    except ValueError as e:
                        logger.warning("Invalid JSON data in metainf file _updater4pyi_metainf.json: %s" %(str(e)))

                # iterate over files to extract with executable permissions set.
                for zinfo in thezipfile.infolist():
                    if zinfo.filename in SPECIAL_ZIP_FILES:
                        continue
                    thezipfile.extract(zinfo, extractto)
                    os.chmod(os.path.join(extractto, zinfo.filename), 0755) # make executable
                thezipfile.close()

                # override some permissions with a special metainfo file.
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

                extractloc.findextractto(namelist=thetarfile.getnames())
                extractto = extractloc.extractto

                thezipfile.extractall(extractto)
                thezipfile.close()

                # remove the temporary downloaded file.
                os.unlink(tmpfile.name)

            else:
                raise Updater4PyiError("Downloaded file %s is not a recognized archive."
                                       %(os.path.basename(tmpfile.name)))

            # now, set installto if we need a sudo install
            extractedfile = os.path.join(extractto, os.path.basename(filetoupdate.fn))
            installto = extractloc.installto

        else:
            # make sure the file is executable
            os.chmod(tmpfile.name,
                     stat.S_IREAD|stat.S_IWRITE|stat.S_IEXEC|
                     stat.S_IRUSR|stat.S_IWUSR|stat.S_IXUSR|
                     stat.S_IRGRP|stat.S_IXGRP|
                     stat.S_IROTH|stat.S_IXOTH
                     )

            if not needs_work_in_temp_dir:
                # following docs: these may be on different filesystems, and docs specify that os.rename()
                # may fail in that case. So use shutil.move() which should work.
                shutil.move(tmpfile.name, filetoupdate.fn)
            else:
                # the ready file, and the install location. This will be installed by the sudo script.
                extractedfile = tmpfile.name
                installto = filetoupdate.fn

        # do possibly the sudo install if needed
        if needs_work_in_temp_dir:
            if util.is_linux() or util.is_macosx():
                res = util.run_as_admin([util.which('bash'),
                                         util.resource_path('updater4pyi/installers/unix/do_install.sh'),
                                         extractto, installto, backupfilename])
                if (res != 0):
                    raise Updater4PyiError("Can't install the update to the final location %s!" %(installto))
            elif util.is_win():
                # first, copy do_install.exe and its dependencies to some path out of the way, and
                # instruct them to auto-destroy.
                doinstalldirname = tempfile.mkdtemp(prefix='upd4pyi_tmp_')
                doinstallzipfile = zipfile.ZipFile(
                    util.resource_path('updater4pyi/installers/win/do_install.exe.zip'),
                    'r')
                doinstallzipfile.extractall(doinstalldirname)
                # now, run do_install.exe
                manage_install_cmd = [os.path.join(doinstalldirname, 'manage_install.exe'),
                                      str(os.getpid()),
                                      ('1' if needs_sudo else '0'),
                                      filetoupdate.fn,
                                      backupfilename,
                                      extractedfile,
                                      installto,
                                      doinstalldirname,
                                      filetoupdate.executable
                                   ]
                logger.debug("Running %r as %s", manage_install_cmd, ("admin" if needs_sudo else "normal user"))
                util.run_win(argv=manage_install_cmd,
                             # manage_install will itself run do_install as sudo if needed. Don't run
                             # manage_install as root, because manage_install is also responsible of
                             # relaunching us.
                             needs_sudo=False,
                             wait=False,
                             cwd=os.path.expanduser("~"), # some path out of our dir, which needs to be deleted.
                             )
                sys.exit(0)
            else:
                logger.error("I don't know your platform to run sudo install on: %s", util.simple_platform())
                raise RuntimeError("Unknown platform for sudo install: %s" %(util.simple_platform()))

    except Exception:
        logger.error("Software Update Error: %s\n" %(str(sys.exc_info()[1])));
        restorebackup()
        raise

    logger.warning("For debugging & possible unstability, NOT removing backup.")
    # remove the backup.
    #if not needs_work_in_temp_dir:
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

    global url_opener

    logger.debug("fetching URL %s to temp file %s ...", theurl, _noexcept(lambda : fdst.name))

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





