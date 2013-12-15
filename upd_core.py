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
from urllib2 import urlopen



class PyInstallerUpdaterError(Exception):
    def __init__(self, msg):
        self(PyInstallerUpdaterError, self).__init__('Software Updater: '+msg);



# --------------------------------------------------------------------------------

_update_source = None
_update_interface = None

def get_update_source():
    return _update_source

def get_update_interface():
    return _update_interface



def install_update_checker(update_source, update_interface=None):
    """
    Installs an update checker, implemented by the source `update_source` (a
    `upd_source.UpdateSource` subclass instance), and the user interface
    `update_interface` (itself an `upd_iface.UpdateInterface` subclass instance).
    """

    if (not hasattr(sys, '_MEIPASS')):
        raise PyInstallerUpdaterError("This installation is not built with pyinstaller.")

    if (update_interface is None):
        from upd_iface import UpdateInterfaceConsole
        update_interface = UpdateInterfaceConsole()
        
    _update_source = update_source
    _update_interface = update_interface

    _update_interface.start(update_source)



# -------------------------------



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




def install_update(update_info, needs_unzip=None ):

    with urlopen(update_info.get_url()) as f:
        if (needs_unzip):
            # feed this directly into a zipfile handler
    
