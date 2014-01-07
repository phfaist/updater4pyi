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
import datetime

from PyQt4.QtCore import *
from PyQt4.QtGui import *

import upd_core
import upd_iface

logger = logging.getLogger('updater4pyi')




class UpdatePyQt4Interface(QObject,upd_iface.UpdateGenericGuiInterface):
    def __init__(self, parent=None, **kwargs):
        self.timer = None
        
        QObject.__init__(self, parent=parent)
        # super doesn't propagate out of the Qt multiple inheritance...
        upd_iface.UpdateGenericGuiInterface.__init__(self, **kwargs)


    # ------------

    def get_settings_object(self):
        """
        Subclasses may reimplement this function to cusomize where the settings are stored.
        """
        settings = QSettings()
        settings.beginGroup('updater4pyi')
        return settings

    def load_settings(self, keylist):
        settings = self.get_settings_object()
        d = {}
        for key in keylist:
            if settings.contains(key):
                d[key] = settings.value(key).toPyObject()

        logger.debug("load_settings: read settings: %r", d)
        return d

    def save_settings(self, d=None):
        if d is None:
            d = self.all_settings()

        logger.debug("save_settings: saving settings: %r", d)

        settings = self.get_settings_object()
        for k,v in d.iteritems():
            settings.setValue(k, QVariant(v))


    def ask_to_update(self, rel_info):
        msgBox = QMessageBox(parent=None)
        msgBox.setWindowModality(Qt.NonModal)
        msgBox.setText(unicode(self.tr("A new software update is available (%sversion %s)."))
                       %(self.progname+' ' if self.progname else '', rel_info.get_version()))
        msgBox.setInformativeText(self.tr("Do you want to install the new version? Please make sure you save all "
                                          "your changes to your files before installing the update."))
        btnInstall = msgBox.addButton("Install", QMessageBox.AcceptRole)
        btnNotNow = msgBox.addButton("Not now", QMessageBox.RejectRole)
        btnDisableUpdates = msgBox.addButton("Disable Update Checks", QMessageBox.RejectRole)
        msgBox.setDefaultButton(btnInstall)
        msgBox.setEscapeButton(btnNotNow)
        msgBox.setIcon(QMessageBox.Question)
        msgBox.exec_()

        clickedbutton = msgBox.clickedButton()

        # btnInstall: install update
        
        if (clickedbutton == btnInstall):
            return True

        # btnNotNow, btnDisableUpdates: don't check for updates
        
        if (clickedbutton == btnDisableUpdates):
            self.setCheckForUpdatesEnabled(False)

        return False
        
        
    def ask_to_restart(self):
        msgBox = QMessageBox(parent=None)
        msgBox.setWindowModality(Qt.NonModal)
        msgBox.setText(self.tr("The software update is now complete."))
        msgBox.setInformativeText(self.tr("This program needs to be restarted for the changes "
                                          "to take effect. Restart now?"))
        btnRestart = msgBox.addButton("Restart", QMessageBox.AcceptRole)
        btnIgnore = msgBox.addButton("Ignore", QMessageBox.RejectRole)

        msgBox.setDefaultButton(btnRestart)
        msgBox.setEscapeButton(btnIgnore)
        msgBox.setIcon(QMessageBox.Information)
        msgBox.exec_();

        clickedbutton = msgBox.clickedButton()

        if (clickedbutton == btnRestart):
            return True

        return False
        
        
    def set_timeout_check(self, interval_timedelta):

        # interval in milliseconds
        interval_ms = int(interval_timedelta.total_seconds()*1000)
        
        if self.timer is None:
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.check_for_updates)
            self.timer.setSingleShot(True)
        elif self.timer.isActive():
            self.timer.stop()

        self.timer.setInterval(interval_ms)
        self.timer.start()
        logger.debug("single-shot timer started with interval=%d ms", interval_ms)


    # add proper slot decorations to these members

    # don't use timedelta, unknown to Qt4, but rather milliseconds (and the rename slot accordingly)
    @pyqtSlot(int)
    def setInitCheckDelayMs(self, init_check_delay_ms, save=True):
        super(UpdatePyQt4Interface, self).setInitCheckDelay(
            datetime.timedelta(days=0, microseconds=init_check_delay_ms*1000),
            save=save
            )

    # don't use timedelta, unknown to Qt4, but rather milliseconds (and the rename slot accordingly)
    @pyqtSlot(int)
    def setCheckIntervalMs(self, check_interval_ms, save=True):
        super(UpdatePyQt4Interface, self).setCheckIntervalMs(
            datetime.timedelta(days=0, microseconds=check_interval_ms*1000),
            save=save
            )

    @pyqtSlot(bool)
    def setCheckForUpdatesEnabled(self, enabled, save=True):
        super(UpdatePyQt4Interface, self).setCheckForUpdatesEnabled(enabled, save=save)
