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
import os
import os.path
import subprocess

import upd_core



class UpdateInterface(object):
    def __init__(self, *args, **pwargs):
        pass

    def start(self, **kwargs):
        """
        Start being aware of wanting to check for updates. It is up to the interface
        to decide when to check for updates, how often, etc. For example, a console
        interface would check right away, while a GUI might first load the application,
        and set a timer to check later, so that startup is not slowed down by the update
        check.
        """
        raise NotImplementedError
    


def restart_app(exe=None):
    if (exe is None):
        exe = upd_core.file_to_update().executable

    if upd_core.is_macosx() or upd_core.is_linux():
        this_pid = os.getpid()
        subprocess.Popen("while ps -x -p %d >/dev/null; do sleep 1; done; %s"
                         %(this_pid, _bash_quote(exe)),
                         shell=True)
        sys.exit(0)
        
    elif upd_core.is_win():
        # TODO: write me! sth like the following, but this needs testing:
        #subprocess.Popen("%s" %(_batch_quote(exe)),
        #                 shell=False)
        #sys.exit(0)
        raise NotImplementedError

    else:
        logger.warning("I don't know about your platform. You'll have to restart this "
                       "program by yourself like a grown-up. I'm exiting now! Have fun.")
        sys.exit(0)

def _bash_quote(x):
    return "'" + x.replace("'", "'\\''") + "'"
def _batch_quote(x):
    return '"' + x + '"'



class UpdateConsoleInterface(UpdateInterface):
    def __init__(self, ask_before_checking=False, *args, **kwargs):
        super(UpdateConsoleInterface, self).__init__(self, *args, **kwargs)
        self.ask_before_checking = ask_before_checking

    def start(self):

        #
        # See if we should ask before checking.
        #
        if (self.ask_before_checking):
            if (not self._ynprompt("Do you wish to check for software updates? (y/n) ")):
                return
            
        #
        # Check for updates.
        #
        upd_info = upd_core.check_for_updates()

        if (upd_info is None):
            # no updates.
            print "No updates available."
            return

        #
        # There's an update, prompt the user.
        #
        print ""
        print "-----------------------------------------------------------"
        print ""
        print "A new software update is available (version %s)" %(upd_info.version)
        print ""

        if (self._ynprompt("Do you want to install it? (y/n) ")):
            #
            # yes, install update
            #
            upd_core.install_update(upd_info)
            #
            # update installed.
            #
            print ""
            print "Update installed. Quitting. Please restart the program."
            print ""
            print "-----------------------------------------------------------"
            print ""
            sys.exit(0)
        else:
            print ""
            print "Not installing update."
            print ""
            print "-----------------------------------------------------------"
            print ""

        # return to the main program.
        return
        
    def _ynprompt(self, msg):
        yn = raw_input(msg)
        return re.match(r'\s*y(es)?\s*', yn, re.IGNORECASE) is not None


