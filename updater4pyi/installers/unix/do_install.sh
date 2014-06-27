#!/bin/bash
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

if [ "$#" -ne 4 ]; then
    echo >&2 "Usage: $0  <BACKUP-WHAT> <BACKUP NAME> <TEMP LOC> <INSTALL LOC>"
    exit 255
fi

backupwhat="$1"
backupname="$2"
temploc="$3"
installloc="$4"

# ----------------------------------------

if [ -n "$backupname" ]; then

    echo -n "Backing up '$backupwhat' to '$backupname' ... "
    mv "$backupwhat" "$backupname"

    if [ "$?" == "0" ]; then
        echo " OK";
    else
        echo " Failed";
        exit 1;
    fi
else

    echo -n "Removing '$backupwhat' ... "
    rm -rf "$backupwhat"

    if [ "$?" == "0" ]; then
        echo " OK";
    else
        echo " Failed";
        exit 2;
    fi
fi

# ----------------------------------------

if [ -n "$temploc" -a -n "$installloc" ]; then

    # install to some location
    echo -n "Installing '$temploc' to '$installloc' ... "
    mv "$temploc" "$installloc"

    if [ "$?" == "0" ]; then
        echo " OK";
    else
        echo " Failed";
        exit 3;
    fi
fi

#  ---------------------------------------

# installation OK, remove backup.

if [ -n "$backupname" ]; then
    echo -n "Removing backup '$backupname' ... "
    rm -rf "$backupname"
    if [ "$?" == "0" ]; then
        echo " OK";
    else
        echo " Failed";
        echo "WARNING: Can't remove backup '$backupname'."
        # still success, because we installed the update, so don't exit with an error code.
    fi
fi


exit 0;
