# -*- coding: utf-8 -*-
#######################################################################################
#                                                                                     #
#   This file is part of the updater4pyi Project.                                     #
#                                                                                     #
#   Copyright (C) 2014, Philippe Faist                                                #
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



# ------------------------------------------------------------------------

# our exception class

class Updater4PyiError(Exception):
    """
    An exception class used to signify an error in the installation of a software update,
    for example.

    However, if you're not digging into the internals of the update interface, you
    probably won't even have to bother with catching these. See also
    :py:class:`~upd_core.Updater` and :py:class:`~upd_iface.UpdateInterface`.
    """
    def __init__(self, msg):
        self.updater_msg = msg
        Exception.__init__(self, 'Software Updater Error: '+msg);




# ------------------------------------------------------------------------

# release package types


RELTYPE_UNKNOWN = 0
"""
Unknown release type.
"""

RELTYPE_EXE = 1
"""
A single executable. For example, a MS Windows .exe file or a linux executable.
"""

RELTYPE_ARCHIVE = 2
"""
An archive containing several files. The archive should be extracted into a directory.
"""

RELTYPE_BUNDLE_ARCHIVE = 3
"""
An archive containing a Mac OS X application bundle.
"""


