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
import zipfile
import tarfile
import json
import glob
import subprocess
import tempfile
import shutil

from . import util
from . import upd_version
from .upd_log import logger
from .upd_defs import RELTYPE_UNKNOWN, RELTYPE_EXE, RELTYPE_ARCHIVE, RELTYPE_BUNDLE_ARCHIVE
from .upd_defs import Updater4PyiError
import upd_downloader


# --------------------------------


FileToUpdate = collections.namedtuple('FileToUpdate', ('fn', 'reltype', 'executable',));


def determine_file_to_update():
    """
    Inspects the program currently running, and determines the location of the file one
    should replace in the event of a software update.

    Returns a named tuple `FileToUpdate(fn=.., reltype=.., executable=...)`. The values
    are:

        - `fn`: the actual file we should update. This could be a directory in the case of
          a onedir PyInstaller package. For a MAC OS X bundle, it is the `XYZ.app` file.
          
        - `reltype`: the release type we have. This may be one of
          :py:const:`upd_defs.RELTYPE_EXE`, :py:const:`upd_defs.RELTYPE_ARCHIVE`,
          :py:const:`upd_defs.RELTYPE_BUNDLE_ARCHIVE`.

        - `executable`: the actual executable file. This may be different from `fn`, for
          example in Mac OS X bundles, where `executable` is the actual file being
          executed within the bundle.

    .. _PyInstaller: http://www.pyinstaller.org/
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





# ------------------------------------------------------------------------

_updater = None

def get_updater():
    return _updater



class Updater(object):
    """
    The main Updater object.

    This class is responsible for actually checking for updates and performing the
    software update.

    It does not take care of scheduling the checks, however. That's done with an
    UpdaterInterface.

    This class needs to be specified a *source* for updates. See
    :py:class:`upd_source.UpdateSource`.
    """
    def __init__(self, current_version, update_source):
        """
        Instantiates an `Updater`, with updates provided by the source `update_source` (a
        `upd_source.UpdateSource` subclass instance).

        The `current_version` is the current version string of the software, and will
        be provided to the `update_source`.
        """

        # sys._MEIPASS seems to be set all the time, even we don't self-extract.
        if (not hasattr(sys, '_MEIPASS')):
            raise Updater4PyiError("This installation is not built with pyinstaller.")

        self._update_source = update_source

        logger.debug("source is %r" %(self._update_source))

        self._current_version = current_version
        self._file_to_update = determine_file_to_update()

        super(Updater, self).__init__()


    def update_source(self):
        """
        Return the source given to the constructor.
        """
        return self._update_source

    def current_version(self):
        """
        Return the current version of the running program, as given to the constructor.
        """
        return self._current_version

    def file_to_update(self):
        """
        Return the file one should update. See :py:func:`determine_file_to_update`.
        """
        return self._file_to_update


    # -------------------------------------------


    def check_for_updates(self):
        """
        Perform an update check.

        Queries the source for possible updates, which matches our system. If a software
        update is found, then a :py:class:`upd_source.BinReleaseInfo` object is returned,
        describing the software update. Otherwise, if no update is available, `None` is
        returned.
        """
        
        releases = self._update_source.get_releases(newer_than_version=self._current_version)

        logger.debug("releases=%r" %(releases))

        if (releases is None):
            logger.warning("Software Update Source returned a None release list!")
            return None

        wanted_reltype = self._file_to_update.reltype

        # this is current version
        curver = util.parse_version(self._current_version)

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
    # methods that perform the software update
    # ------------------------------------------
    

    SPECIAL_ZIP_FILES = ('_updater4pyi_metainf.json',
                         '_METAINF',
                         )

    # internal
    class _ExtractLocation(object):
        def __init__(self, filetoupdate, needs_sudo, **kwargs):
            self.filetoupdate = filetoupdate
            self.needs_sudo = needs_sudo

            super(Updater._ExtractLocation, self).__init__(**kwargs)


        def findextractto(self, namelist):

            (basedir, basefn) = os.path.split(self.filetoupdate.fn)

            self.extractto = None
            self.installto = None
            self.extracttotemp = False

            self.extractstodir = True
            if ([True for x in namelist if not x.startswith(basefn) and x not in Updater.SPECIAL_ZIP_FILES]):
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


    # ------------------------------------------------
    # Install a Given Update
    # ------------------------------------------------
    def install_update(self, rel_info):
        """
        Install a given update. `rel_info` should be a
        :py:class:`upd_source.BinReleaseInfo` returned by :py:meth:`check_for_updates`.

        The actual updates are downloaded by calling :py:meth:`download_file`. You may
        overload that function if you need to customize the download process. You may also
        override :py:meth:`verify_download` to implement some download integrity verification.

        This function does not return anything. If an error occurred,
        :py:exc:`upd_defs.Updater4PyiError` is raised.
        """

        # first, save the file locally.
        tmpfile = tempfile.NamedTemporaryFile(mode='w+b', prefix='upd4pyi_tmp_', dir=None, delete=False)

        url = rel_info.get_url();

        try:
            self.download_file(url, tmpfile)
        except IOError as e: 
            if hasattr(e, 'code'): # HTTPError 
                raise Updater4PyiError('Got HTTP error: %d %s' %(e.code, e.reason))
            elif hasattr(e, 'reason'): # URLError 
                raise Updater4PyiError('Connection error: %s' %(e.reason))
            else:
                raise Updater4PyiError('Error: %s' %(str(e)))

        #
        # Verify download integrity
        #
        if (not self.verify_download(rel_info, tmpfile)):
            logger.warning("Failed to download %s : download verification failed.", url);
            os.unlink(tmpfile);
            raise Updater4PyiError("Failed to download software update: verification failed.")

        # at this point, file is downloaded and on disk.

        # the file/directory we have to update.
        filetoupdate = self._file_to_update;

        # do we need superuser access for performing the install?
        needs_sudo = not (util.locationIsWritable(filetoupdate.fn) and
                          util.dirIsWritable(os.path.dirname(filetoupdate.fn)))


        # determine if we will work in the temporary dir only and call an external utility (e.g. do_install.exe)
        # or if we will directly unpack e.g. the zip file at the right location.
        #
        # reasons for staying in temp locations are:
        #   * final location requires root access
        #   * windows: can't overwrite files of the running process.
        needs_work_in_temp_dir = needs_sudo or util.is_win();

        logger.debug("installation will need sudo? %s", needs_sudo)

        reltype_is_dir = filetoupdate.reltype in (RELTYPE_BUNDLE_ARCHIVE,
                                                  RELTYPE_ARCHIVE);

        extractedfile = None
        installto = None
        extractloc = None


        def cleanuptempfiles():
            if (tmpfile.name and os.path.exists(tmpfile.name)):
                logger.debug("cleaning up maybe %s", tmpfile.name)
                util.ignore_exc(lambda : os.unlink(tmpfile.name), OSError)

            if extractloc is not None and extractloc.extracttotemp and os.path.exists(extractloc.extractto):
                logger.debug("cleaning up maybe %s", extractloc.extractto)
                util.ignore_exc(lambda : shutil.rmtree(extractloc.extractto), OSError)


        # move that file out of the way, but keep it as backup. So just rename it.
        backupfilename = _backupname(filetoupdate.fn)
        if not needs_work_in_temp_dir:
            try:
                os.rename(filetoupdate.fn, backupfilename);
            except OSError as e:
                cleanuptempfiles();
                raise Updater4PyiError("Failed to rename file %s!" %(str(e)))



        def failure_cleanupandrestorebackup():
            # files may have been downloaded/extracted to some location

            cleanuptempfiles()

            if extractedfile and os.path.exists(extractedfile):
                logger.debug("cleaning up maybe %s", extractedfile)
                util.ignore_exc(lambda : shutil.rmtree(extractedfile), OSError)

            if needs_work_in_temp_dir:
                # no backup was generated anyway at this point
                return

            logger.debug("cleaning up maybe %s", filetoupdate.fn)
            util.ignore_exc(lambda : shutil.rmtree(filetoupdate.fn), OSError)

            try:
                logger.debug("restoring backup %s -> %s", backupfilename, filetoupdate.fn)
                shutil.move(backupfilename, filetoupdate.fn)
            except OSError as e:
                logger.error("Software Update Error: Failed to restore backup %s of %s! %s\n"
                             % (backupfilename, filetoupdate.fn, str(e)))

            return


        try:
            if (reltype_is_dir):
                # we are updating the directory itself. So make sure we download an archive file.

                extractloc = Updater._ExtractLocation(filetoupdate=filetoupdate,
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
                        if zinfo.filename in Updater.SPECIAL_ZIP_FILES:
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

                # also, check that we've extracted a valid archive which replaces the same file.
                fnreltoextract = os.path.relpath(filetoupdate.executable, start=filetoupdate.fn);
                if not os.path.exists(os.path.join(extractedfile, fnreltoextract)):
                    logger.error("Update package doesn't contain file %s in %s",
                                 fnreltoextract, extractedfile);
                    raise Updater4PyiError("Update package is malformed: can't find executable");

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
                                             filetoupdate.fn, backupfilename, extractedfile, installto])
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
            failure_cleanupandrestorebackup()
            raise

        # cleaning up temp files
        logger.debug("cleaning up temp files")
        cleanuptempfiles()

        # remove the backup.
        if not needs_work_in_temp_dir:
            #DEBUG: logger.warning("For debugging & possible unstability, NOT removing backup.")
            if (reltype_is_dir):
                logger.debug("removing backup directory %s", backupfilename)
                try:
                    shutil.rmtree(backupfilename)
                except (OSError,IOError):
                    logger.warning("Failed to remove backup directory %s !", backupfilename)
                    # e.g. this might happen if the executable is on some filesystems such as sshfs
            else:
                logger.debug("removing backup file %s", backupfilename)
                try:
                    os.unlink(backupfilename)
                except (OSError,IOError):
                    logger.warning("Failed to remove backup file %s !", backupfilename)



    def download_file(self, theurl, fdst):
        """
        Download the file given at location `theurl` to the destination file `fdst`.

        You may reimplement this function to customize the download process. Check out
        `upd_downloader.url_opener` if you want to download stuff from an HTTPS url, it
        may be useful.

        The default implementation downloads the file with the `upd_downloader` utility
        which provides secure downloads with certificate validation for HTTPS downloads.

        This function should return nothing. If an error occurs, this function should
        raise an `IOError`.
        """

        logger.debug("fetching URL %s to temp file %s ...", theurl, util.ignore_exc(lambda : fdst.name))

        fdata = upd_downloader.url_opener.open(theurl);
        shutil.copyfileobj(fdata, fdst)
        fdata.close()
        fdst.close()

        logger.debug("... done.")


    def verify_download(self, rel_info, tmpfile):
        """
        Verify the integrity of the downloaded file. Return `True` if the download
        succeeded or `False` if not.

        Arguments:

            - `rel_info` is the release information as a
              :py:class:`upd_source.BinReleaseInfo` instance, as given to
              :py:meth:`install_update`.

            - `tmpfile` is a python :py:class:`tempfile.NamedTemporaryFile` instance
              where the file was downloaded. This function should in principle check
              the validity of the contents of this file.

        You may reimplement this function to implement integrity check. The default
        implementation does nothing and returns `True`.

        Don't raise arbitrary exceptions here because they might not be caught. You may
        raise :py:exc:`upd_defs.Updater4PyiError` for serious errors, though.
        """
        # TODO: add support for GPG signing, MD5/SHA-1 checksum checks etc... ???
        # Note: might not be necessary with secure https downloads with checked certificate
        return True


    # ---------------------------------------------------------------

    # utility: restart this application

    def restart_app(self):
        """
        Utility to restart the application. This is meant for graphical applications which
        start in the background.

        The application exit is done by calling ``sys.exit(0)``.
        """

        exe = self._file_to_update.executable

        # the exe_cmd

        if util.is_macosx() or util.is_linux():
            exe_cmd = util.bash_quote(exe)

            if (util.is_macosx() and
                exe == self._file_to_update.executable and
                self._file_to_update.fn.lower().endswith('.app')):
                # Mac OS X, we are launching this exact executable, which is known to be a .app;
                # --> use 'open FooBar.app' instead.
                exe_cmd = 'open '+util.bash_quote(self._file_to_update.fn) # the .app

            this_pid = os.getpid()
            subprocess.Popen("while ps -p %d >/dev/null; do sleep 1; done; ( %s & )"
                             %(this_pid, exe_cmd),
                             shell=True)
            sys.exit(0)

        elif util.is_win():
            # we don't need to implement this, on windows the external process manage_install.exe
            # also takes care of restarting us.
            raise RuntimeError("Can't use restart_app on windows. The manage_install.exe process already "
                               "takes care of that.")

        else:
            logger.warning("I don't know about your platform. You'll have to restart this "
                           "program by yourself like a grown-up. I'm exiting now! Have fun.")
            sys.exit(0)


            
# --------------------------------------------------------------
    

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





