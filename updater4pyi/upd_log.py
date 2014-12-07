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
Set up a minimal logger. To integrate logging in your application, configure your Python
`logging`_ as you wish. Updater4Pyi gets its logger by calling
``logging.getLogger('updater4pyi')``, i.e. the Updater4Pyi's logger is called
'updater4pyi'.

.. _logging: https://docs.python.org/2/library/logging.html

"""

import logging


# the logger.
# Note that we can do 'from upd_log import logger'
logger = logging.getLogger('updater4pyi');


# the formatter
formatter = logging.Formatter('%(name)s - %(asctime)-15s\n\t%(levelname)s: %(message)s');



def setup_logger(level=logging.INFO):
    """
    A utility function that you can call to set up a simple logging to the console. No
    hassles.
    """
    
    # create console handler
    ch = logging.StreamHandler();
    ch.setLevel(logging.NOTSET); # propagate all messages
    
    # add the formatter to the handler
    ch.setFormatter(formatter);
    
    # add the handlers to the logger
    logger.addHandler(ch);

    # set the logger's level
    logger.setLevel(level);

    logger.debug("logger set up. level=%d", level)
    
