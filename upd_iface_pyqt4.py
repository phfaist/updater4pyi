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

import logging

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import upd_core
import upd_iface

logger = logging.getLogger('updater4pyi')



# initial check by default 1 minute after app startup
DEFAULT_INIT_CHECK_DELAY = 60*1000
# subsequent checks every 6 hours by default
DEFAULT_CHECK_INTERVAL = 6*60*60*1000


class UpdatePyQt4Interface(QObject,upd_iface.UpdateInterface):
    def __init__(self, init_check_delay=DEFAULT_INIT_CHECK_DELAY, check_interval=DEFAULT_CHECK_INTERVAL,
                 parent=None):
        self.init_check_delay = init_check_delay
        self.check_interval = check_interval

        self.timer = None
        self.is_initial_delay = None
        super(UpdatePyQt4Interface, self).__init__(parent=parent)
        # super doesn't propagate out of the Qt multiple inheritance...
        upd_iface.UpdateInterface.__init__(self)
    
    def start(self):
        logger.debug("Starting interface (pyqt4)")
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.slotTimeout)

        self.is_initial_delay = True
        self.timer.setSingleShot(True)
        self.timer.setInterval(self.init_check_delay)
        self.timer.start()

        logger.debug("single-shot timer started with interval=%d" %(self.init_check_delay))


    @pyqtSlot()
    def slotTimeout(self):
        logger.debug("pyqt4 interface: slotTimeout()")
        
        try:
            # check for updates

            rel_info = upd_core.check_for_updates()

            if (rel_info is None):
                # no updates.
                logger.debug("upd_iface_pyqt4: No updates available.")
                return

            #
            # There's an update, prompt the user.
            #
            if self.ask_to_update(rel_info):
                #
                # yes, install update
                #
                upd_core.install_update(rel_info)
                #
                # update installed.
                #
                if self.ask_to_restart():
                    upd_iface.restart_app()
                    return

            else:
                logger.debug("Not installing update.")


            # return to the main program.
            return
        
        finally:
            # configure the timer to tick in check_interval milliseconds from now.
            self.is_initial_delay = False # also, we're no longer in the first initial delay.
            self.timer.setSingleShot(True)
            self.timer.setInterval(self.check_interval)
            self.timer.start()



    def ask_to_update(self, rel_info):
        resp = QMessageBox.question(None, self.tr("Software Update", "Updater4Pyi"),
                                    str(self.tr("A new software update is available (version %s). "
                                                "Do you want to install it?", "Updater4Pyi"))
                                    %(rel_info.version),
                                    QMessageBox.Yes|QMessageBox.Cancel, QMessageBox.Yes)

        return resp == QMessageBox.Yes
        
    def ask_to_restart(self):
        resp = QMessageBox.information(None, self.tr("Update Complete.", "Updater4Pyi"),
                                       self.tr("The Update completed successfully. This program needs to be "
                                                  "restarted for the changes to take effect. Restart now?",
                                               "Updater4Pyi"),
                                       QMessageBox.Yes|QMessageBox.No, QMessageBox.Yes)
        return resp == QMessageBox.Yes
        
