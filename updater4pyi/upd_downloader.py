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

"""
Utilities to download files over secure HTTPS connections, with *server certificate
verification*.

See `Validate SSL certificates with Python <http://stackoverflow.com/q/1087227/1694896>`_
and and `this solution <http://stackoverflow.com/a/14320202/1694896>`_ on Stack Overflow.
"""

import logging

import httplib
import ssl
import socket
import shutil
import urllib2

from . import upd_version
from . import util
from .upd_log import logger


# -------------------------------

CERT_FILE = util.resource_path('updater4pyi/cacert.pem');

class ValidHTTPSConnection(httplib.HTTPConnection):
    """
    HTTPS connection based on httplib.HTTPConnection, with complete certificate validation
    based on known root certificates packaged with the program.

    The root certificate file is given in the module-level variable
    :py:data:`CERT_FILE`. Note you may use :py:func:`util.resource_path` to get a file in
    the pyinstaller bundle.
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
    """
    A HTTPS urllib2 handler using :py:class:`ValidHttpsConnection`, i.e. with correct
    server certificate validation.
    """

    def https_open(self, req):
            return self.do_open(ValidHTTPSConnection, req)



url_opener = urllib2.build_opener(ValidHTTPSHandler)
"""
The URL opener obtained with `urllib2.build_opener`, with valid HTTPS server certificate
validation.
"""

# add a User-agent header
url_opener.addheaders = [('User-agent', 'Updater4Pyi-SoftwareUpdater %s'%(upd_version.version_str))]

