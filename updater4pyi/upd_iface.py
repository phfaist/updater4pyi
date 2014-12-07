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
import datetime

from . import util
from .upd_defs import Updater4PyiError
from .upd_log import logger



class UpdateInterface(object):
    def __init__(self, updater, progname=None, **kwargs):
        self.updater = updater
        self.progname = progname
        super(UpdateInterface, self).__init__(**kwargs)

    def start(self, **kwargs):
        """
        Start being aware of wanting to check for updates. It is up to the interface
        to decide when to check for updates, how often, etc. For example, a console
        interface would check right away, while a GUI might first load the application,
        and set a timer to check later, so that startup is not slowed down by the update
        check.
        """
        raise NotImplementedError




# -----------




class UpdateConsoleInterface(UpdateInterface):
    """
    A very simple :py:class:`UpdateInterface` implementation that checks for updates each
    time the program is run. This is mostly meant for debugging purposes.
    """
    def __init__(self, updater, ask_before_checking=False, **kwargs):
        super(UpdateConsoleInterface, self).__init__(updater=updater, **kwargs)
        self.ask_before_checking = ask_before_checking


    def start(self):

        try:
            
            self._runupdatecheck();
            
        except Updater4PyiError as e:
            print "\n"
            print "------------------------------------------------------------"
            print "Error: %s" % (e)
            print "Software update aborted."
            print "------------------------------------------------------------"
            print "\n"
            return

        # return to the main program.
        return


    def _runupdatecheck(self):
        #
        # See if we should ask before checking.
        #
        if (self.ask_before_checking):
            if (not self._ynprompt("Do you wish to check for software updates? (y/n) ")):
                return

        #
        # Check for updates.
        #
        upd_info = self.updater.check_for_updates()

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
        print ("A new software update is available (%sversion %s)"
               % (self.progname+" " if self.progname else "", upd_info.version))
        print ""

        if (self._ynprompt("Do you want to install it? (y/n) ")):
            #
            # yes, install update
            #
            self.updater.install_update(upd_info)
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
        
        
    def _ynprompt(self, msg):
        yn = raw_input(msg)
        return re.match(r'\s*y(es)?\s*', yn, re.IGNORECASE) is not None




# ---------------------------------------------------------------------




# initial check by default 1 minute after app startup, so as not to slow down app startup.
DEFAULT_INIT_CHECK_DELAY = datetime.timedelta(days=0, seconds=60, microseconds=0)
# subsequent checks every week by default
DEFAULT_CHECK_INTERVAL = datetime.timedelta(days=7, seconds=0, microseconds=0)


_SETTINGS_ALL = ['check_for_updates_enabled', 'init_check_delay', 'check_interval',
                 'last_check']

class UpdateGenericGuiInterface(UpdateInterface):
    def __init__(self, updater, ask_before_checking=True, **kwargs):
        super(UpdateGenericGuiInterface, self).__init__(updater, **kwargs)

        self.ask_before_checking = ask_before_checking;
        
        self.update_installed = False
        self.is_initial_delay = True

        self.is_currently_checking = False

        # load settings
        d = self.load_settings(self._settings_all_keys())
        self.init_check_delay = util.ensure_timedelta(d.get('init_check_delay', DEFAULT_INIT_CHECK_DELAY))
        self.check_interval = util.ensure_timedelta(d.get('check_interval', DEFAULT_CHECK_INTERVAL))

        try:
            val = d.get('check_for_updates_enabled', True)
            self.check_for_updates_enabled = util.getbool(val)
        except ValueError:
            logger.warning("Couldn't parse config value for `check_for_updates_enabled': %r", val)
            self.check_for_updates_enabled = False

        self.last_check = util.ensure_datetime(d.get('last_check', datetime.datetime(1970, 1, 1)))
        if (self.ask_before_checking):
            self.asked_before_checking = d.get('asked_before_checking', False);
        
    
    def start(self):
        logger.debug("Starting interface (generic gui)")
        self.schedule_next_update_check()


    # properties

    def initCheckDelay(self):
        return self.init_check_delay

    def setInitCheckDelay(self, init_check_delay, save=True):
        self.init_check_delay = util.ensure_timedelta(init_check_delay)
        if save:
            self.save_settings({'init_check_delay': self.init_check_delay})

    def checkInterval(self):
        return self.check_interval

    def setCheckInterval(self, check_interval, save=True):
        self.check_interval = util.ensure_timedelta(check_interval)
        if save:
            self.save_settings({'check_interval': self.check_interval})

    def checkForUpdatesEnabled(self):
        return self.check_for_updates_enabled

    def setCheckForUpdatesEnabled(self, enabled, save=True, schedule_check=True):
        self.check_for_updates_enabled = util.getbool(enabled)
        # save setting to settings file
        if save:
            self.save_settings({'check_for_updates_enabled': self.check_for_updates_enabled})
        # also, schedule the next update check
        if schedule_check:
            self.schedule_next_update_check()

    def lastCheck(self):
        return self.last_check

    def setLastCheck(self, last_check, save=True):
        self.last_check = util.ensure_datetime(last_check)
        if save:
            self.save_settings({'last_check': self.last_check})


    # ------------

    def all_settings(self):
        """
        Utility to get all settings. Useful for subclasses; this doesn't need to be reimplemented.
        """
        return dict([(k,getattr(self,k)) for k in self._settings_all_keys()])


    def _settings_all_keys(self):
        """
        Returns a list of relevant settings keys for this object. Includes `'aksed_before_checking'` only
        if the `ask_before_checking` argument given to the constructor was `True`.
        """
        return _SETTINGS_ALL + (['asked_before_checking'] if self.ask_before_checking else [])

    # ----------------------------------------------

    def check_for_updates(self):
        """
        Perform a possible update check. You don't have to reimplement this function, the default
        implementation should be good enough and relies on your implementations of `ask_to_update()`
        and `ask_to_restart()`.

        If the update check isn't due yet, this function does not do the update check. If
        you want to force an update check, call `do_check_for_updates()`.
        """
        logger.debug("UpdateGenericGuiInterface: check_for_updates()")

        if (self.update_installed):
            logger.warning("We have already installed an update and pending restart.")
            return

        logger.debug("self.is_initial_delay=%r, self.timedelta_remaining_to_next_check()=%r",
                     self.is_initial_delay, self.timedelta_remaining_to_next_check())

        # if we were called just after the initial delay, reset this flag.
        if (self.is_initial_delay):
            self.is_initial_delay = False

        # now, really check that we are due for software update check.
        #   * we might be after an initial delay, and while the app was just started, updates are checked
        #     for eg. once a month and a check is not yet due, yet this function is called by timeout.
        #   * even if we are not at the initial delay, the user may have disabled update checks in the
        #     settings between the scheduling of the update check and now.
        if (not self.is_check_now_due()):
            # software update check is not yet due (not even in the next 10 seconds). Just
            # schedule next check.
            logger.debug("Update check is not yet due. Postpone.")
            self.schedule_next_update_check()
            return

        try:
            self.do_check_for_updates()
        finally:
            self.schedule_next_update_check()


    def do_check_for_updates(self):
        """
        Actually perform the udpate check. Call this function if you want to force an
        update check even though it's not yet due. If you want to periodically possibly
        check only if a check is due, then call `check_for_updates()` instead.

        Returns:
            - `None` if we asked the user for the first time if they want to check
              regularly for updates, and they refused.
            - `False` if no new update is available
            - a tuple if a new update is available:
                - `(True, rel_info)` if the user installed the update but did not
                  restart the app;
                - `(False, rel_info)` if the user declined to install the update now
            - the tuple `(False, None, error_str)` if an error occurred while checking
              for updates.
        """
        if self.is_currently_checking:
            return None
        try:
            self.is_currently_checking = True

            # check for updates

            if (self.ask_before_checking and not self.asked_before_checking):
                # ask before we check.
                logger.debug("UpdateGenericGuiInteface: this is the first time. Let's ask the user "
                             "if (s)he's cool with us auto-updating..")
                answer = self.ask_first_time()
                self.setCheckForUpdatesEnabled(answer, save=False);
                self.asked_before_checking = True
                self.save_settings({
                    'asked_before_checking': True,
                    'check_for_updates_enabled': answer,
                    })
                if (answer != True):
                    logger.debug("UpdateGenericGuiInterface: are told not to check for updates.");
                    return None

            rel_info = self.updater.check_for_updates()

            if (rel_info is None):
                # no updates.
                logger.debug("UpdateGenericGuiInterface: No updates available.")
                return False

            logger.debug("Update (version %s) is available.", rel_info.get_version())

            #
            # There's an update, prompt the user.
            #
            if self.ask_to_update(rel_info):
                #
                # yes, install update
                #
                # make sure we save our settings now in case we restart later
                #
                self.save_settings()
                #
                # And actually install the update.
                #
                self.updater.install_update(rel_info)
                self.update_installed = True
                #
                # update installed.
                #
                if self.ask_to_restart():
                    self.updater.restart_app()
                    return (True, rel_info) # whatever, our app will have exited anyway

                # return to the main program.
                return (True, rel_info)

            logger.debug("UpdateGenericGuiInterface: Not installing update.")
            # return to the main program.
            return (False, rel_info)
        
        except Updater4PyiError as e:
            logger.warning("Error while checking for updates: %s", e)
            return (False, None, unicode(e))
            
        finally:
            self.last_check = datetime.datetime.now()
            self.save_settings({'last_check': self.last_check})
            self.is_currently_checking = False


    def is_check_now_due(self, tolerance=datetime.timedelta(days=0, seconds=10)):
        return (self.check_for_updates_enabled and
                self.timedelta_remaining_to_next_check() <= tolerance)

    def schedule_next_update_check(self):
        if not self.check_for_updates_enabled:
            logger.debug("UpdateGenericGuiInterface: Not scheduling update check because we were "
                         "asked not to check for updates.")
            return

        if self.is_currently_checking:
            logger.debug("UpdateGenericGuiInteface: Not scheduling update check because we're currently "
                         "checking for updates!")

        if (self.is_initial_delay):
            self.set_timeout_check(self.init_check_delay)
            logger.debug("UpdateGenericGuiInterface: requested initial single-shot timer for %r seconds"
                         %(self.init_check_delay))
        else:
            timedelta_remaining = self.timedelta_remaining_to_next_check()
            if (timedelta_remaining <= datetime.timedelta(0)):
                logger.debug("UpdateGenericGuiInterface: software update check due now already, checking")
                self.check_for_updates()
                return
            self.set_timeout_check(timedelta_remaining)
            logger.debug("UpdateGenericGuiInterface: requested single-shot timer for %r",
                         timedelta_remaining)


    def timedelta_remaining_to_next_check(self):
        return ((self.last_check + self.check_interval) - datetime.datetime.now())



    # ------------------------------------------------------------------------------
    # the following methods need to be reimplemented, using the gui toolkit at hand.
    # ------------------------------------------------------------------------------
    

    def ask_first_time(self):
        """
        Subclasses should prompt the user whether they want to regularly look for updates.

        This is prompted to the user only if the main program set `ask_before_checking` to `True` in the
        constructor of this object.
        
        Return TRUE if the program should regularly check for updates, or FALSE if not.
        """
        raise NotImplementedError
        
    def ask_to_update(self, rel_info):
        """
        Subclasses should prompt the user whether they want to install the update `rel_info` or not.
        
        Note: Interfaces may also present additional buttons such as "Never check for updates", or
        "Skip this update", and set properties and/or settings accordingly with e.g.
        `setCheckForUpdatesEnabled()`.
        
        Return TRUE if the program should be restarted, or FALSE if not.
        """
        raise NotImplementedError
        
    def ask_to_restart(self):
        """
        Subclasses should prompt the user to restart the program after a successful update.

        Return TRUE if the program should be restarted, or FALSE if not.
        """
        raise NotImplementedError
        
    def set_timeout_check(self, interval_timedelta):
        """
        Subclasses should reimplement this function to call the function `check_for_updates()` after
        `interval_timedelta`. `interval_timedelta` is a `datetime.timedelta` object.
        """
        raise NotImplementedError

    def load_settings(self, keylist):
        """
        Subclasses may reimplement this function to cusomize where and how the settings are stored,
        usually using a toolbox-specific utility, such as QSettings in PyQt4.
        """
        raise NotImplementedError

    def save_settings(self, d=None):
        """
        Save the given settings in the dictionary `d` to some local settings. If d is None, then
        all settings should be saved, effectively taking `d` to be the dictionary returned by
        `all_settings()`.
        """
        raise NotImplementedError



