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
import inspect
import os.path
import collections

import tempfile
import httplib
import ssl
from urlparse import urlparse
import shutil

import upd_version




class Updater4PyiError(Exception):
    def __init__(self, msg):
        self.updater_msg = msg
        self(PyInstallerUpdaterError, self).__init__('Software Updater Error: '+msg);



# --------------------------------------------------------------------------------

_update_source = None
_update_interface = None

def get_update_source():
    return _update_source

def get_update_interface():
    return _update_interface



def setup_updater(current_version, update_source, update_interface=None):
    """
    Installs an update checker, implemented by the source `update_source` (a
    `upd_source.UpdateSource` subclass instance), and the user interface
    `update_interface` (itself an `upd_iface.UpdateInterface` subclass instance).

    The `current_version` is the current version string of the software, and will
    be provided to the `udpate_source`.
    """

    # sys._MEIPASS seems to be set all the time, even we don't self-extract.
    if (not hasattr(sys, '_MEIPASS')):
        raise PyInstallerUpdaterError("This installation is not built with pyinstaller.")

    if (update_interface is None):
        from upd_iface import UpdateConsoleInterface
        update_interface = UpdateConsoleInterface()
        
    _update_source = update_source
    _update_interface = update_interface

    _update_source.set_current_version(current_version)
    _update_source.set_file_to_update(pyi_file_to_update())

    _update_interface.start(update_source)



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




FileToUpdate = namedtuple('FileToUpdate', ('fn', 'is_dir',));


def pyi_file_to_update():
    """
    Returns a FileToUpdate(fn=.., is_dir=..) named tuple.
    """
    
    updatefile = os.path.realpath(sys.executable);
    is_dir = False;

    if (sys.platform.startswith('darwin')):
        # see if we are a Mac OS X bundle
        (lastdir,fn) = os.path.split(sys.executable);
        (beforelastdir,junk) = os.path.split(lastdir);

        if (lastdir == 'MacOS' and beforelastdir == 'Contents'):
            # we're in a Mac OS X bundle, so the actual "executable" should point to the .app file
            is_dir = True
            (updatefile,junk) = os.path.split(beforelastdir);
    else:
        if (hasattr(sys, '_MEIPASS')):
            meipass = os.path.realpath(sys._MEIPASS);
            if (updatefile.startswith(meipass)):
                # pyinstaller files are installed directly: it's the dir we need to update
                is_dir = True;
                updatefile = meipass;


    return FileToUpdate(fn=updatefile, is_dir=is_dir)



def install_update(update_info):

    # first, save the file locally.
    tmpfile = tempfile.NamedTemporaryFile(mode='w+b', prefix='upd4pyi_tmp_', dir=None, delete=False)

    url = update_info.get_url();

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
    filetoupdate = pyi_file_to_update()

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
            os.rename(backupfilename, filetoupdate.fn)
        except OSError:
            sys.stderr.write("WARNING: Failed to restore backup %s of %s!\n"
                             % (backupfilename, filetoupdate.fn))
            pass


    try:
        if (filetoupdate.is_dir):
            # we are updating the directory itself. So make sure we download a ZIP file.
            thezipfile = ZipFile(tmpfile.name, 'r')
            # extract the ZIP file to our directory.

            extractto = None
            namelist = thezipfile.namelist()
            (basedir, basefn) = os.path.split(filetoupdate.fn)
            if ([True for x in namelist if not x.startswith(basefn)]):
                # the zip file doesn't extract into a single dir--there are files with different prefixes.
                # so extract into a single dir ourselves.
                try:
                    os.mkdir(filetoupdate.fn)
                except OSError as e:
                    raise Updater4PyiError("Failed to create directory %s!" %(filetoupdate.fn))

                extractto = filetoupdate.fn
            else:
                extractto = basedir

            thezipfile.extractall(extractto)
            thezipfile.close()
            
            # remove the temporary downloaded file.
            os.unlink(tmpfile)

        else:
            # following docs: these may be on different filesystems, and docs specify that os.rename()
            # may fail in that case. So use shutil.move() which should work.
            shutil.move(tmpfile.name, filetoupdate.fn)

    except:
        sys.stderr.write("Software Update Error: %s\n" %(str(sys.exc_info()[1])));
        restorebackup()
        raise

    # remove the backup.
    #if (filetoupdate.is_dir):
    #    shutil.rmtree(backupfilename)
    #else
    #    os.unlink(backupfilename)
    
    

def _backupname(filename):
    try_suffix = '.bkp'
    while (n < 999 and os.path.exists(filename+try_suffix)):
        try_suffix = '.'+str(n)+'.bkp'
        n += 1;
    if (os.path.exists(filename+try_suffix)):
        raise Updater4PyiError("Can't figure out a backup name for file %s!!" %(filename))
    return filename+try_suffix;





def download_file(theurl, fdst):

    with url_opener.open(update_info.get_url()) as fdata:
        shutil.copyfileobj(fdata, fdst)

    fdst.close()

