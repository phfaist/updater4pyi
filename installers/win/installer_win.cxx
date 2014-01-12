/*#####################################################################################
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
#####################################################################################*/

#include <stdio.h>
#include <stdlib.h>
#include <libgen.h>
#include <string.h>

#include <windows.h>
#include <tchar.h>
#include <shellapi.h>

#include "instcommon.h"

enum {
  ARG_BKP_WHAT = 1,
  ARG_BKP_NAME,
  ARG_MOVE_FROM,
  ARG_MOVE_TO,
  // this one is equal to the reqested argc number:
  ARG_ONE_PAST_LAST
};


int cleanup_from(char *argv_move_from)
{
  // =====================
  // finally, remove empty dir containing the move_from source.

  char move_from_cpy[BUFFER_SIZ];
  if (strlen(argv_move_from) >= BUFFER_SIZ)
    return 15;
  strcpy(move_from_cpy, argv_move_from);
  char *move_from_dname = dirname(move_from_cpy);
  if (strlen(move_from_dname) > strlen("upd4pyi_tmp_xtract_??????") &&
      strncmp(move_from_dname+strlen(move_from_dname)-strlen("upd4pyi_tmp_xtract_??????"),
              "upd4pyi_tmp_xtract_",
              strlen("upd4pyi_tmp_xtract_")) == 0) {
    // move_from's dirname ends with "upd4pyi_tmp_xtract_??????", which is the temp directory
    // in which the software updater extracted the archive. So delete that dir, too.
    TCHAR t_move_from_dname[BUFFER_SIZ];
    if (copy_to_pczztchar(t_move_from_dname, move_from_dname, BUFFER_SIZ))
      return 15;

    SHFILEOPSTRUCT shcl;
    shcl.hwnd = NULL;
    shcl.wFunc = FO_DELETE;
    shcl.pFrom = t_move_from_dname;
    shcl.pTo = NULL;
    shcl.fFlags = FOF_NOCONFIRMATION|FOF_NOCONFIRMMKDIR;
    shcl.lpszProgressTitle = "";

    fprintf(stderr, "Cleaning up %s ...\n", move_from_dname);
    int rescl = SHFileOperation(&shcl);
    if (rescl != 0) {
      fprintf(stderr, "Error cleaning up %s\n", move_from_dname);
      return 3;
    }
  }

  return 0;
}

int failure_restore_backup(TCHAR *bkp_what, TCHAR *bkp_name, char *argv_bkp_what, char *argv_bkp_name)
{
  // =================
  // clean up our mess

  if ( ! (INVALID_FILE_ATTRIBUTES == GetFileAttributes(bkp_what) &&
          ERROR_FILE_NOT_FOUND == GetLastError()) ) {

    // we need to clean up our mess
    SHFILEOPSTRUCT shcln;
    shcln.hwnd = NULL;
    shcln.wFunc = FO_DELETE;
    shcln.pFrom = bkp_what;
    shcln.pTo = NULL;
    shcln.fFlags = FOF_NOCONFIRMATION|FOF_NOCONFIRMMKDIR;
    shcln.lpszProgressTitle = "";

    fprintf(stderr, "Cleaning up %s ...\n", argv_bkp_what);
    int rescln = SHFileOperation(&shcln);
    if (rescln != 0) {
      fprintf(stderr, "Error cleaning up %s: error code %d\n", argv_bkp_what, rescln);
      return 50;
    }
  }

  // ==================
  // and restore backup

  SHFILEOPSTRUCT shbkprest;
  shbkprest.hwnd = NULL;
  shbkprest.wFunc = FO_MOVE;
  shbkprest.pFrom = bkp_name;
  shbkprest.pTo = bkp_what;
  shbkprest.fFlags = FOF_NOCONFIRMATION|FOF_NOCONFIRMMKDIR;
  shbkprest.lpszProgressTitle = "";

  fprintf(stderr, "Restoring Backup %s to %s ...\n", argv_bkp_name, argv_bkp_what);
  int resbkprest = SHFileOperation(&shbkprest);
  if (resbkprest != 0) {
    fprintf(stderr, "Error restoring backup %s to %s: error code %d\n",
            argv_bkp_name, argv_bkp_what, resbkprest);
    return 51;
  }

  return 0;
}



int main(int argc, char **argv)
{
  if (argc != ARG_ONE_PAST_LAST) {
    fprintf(stderr,
            "Usage: %s  <backup-what> <backup-name> <move-from> <move-to>\n",
            argv[0]);
    pause();
    return 100;
  }

  // bkp_what
  TCHAR bkp_what[BUFFER_SIZ];
  if (copy_to_pczztchar(bkp_what, argv[ARG_BKP_WHAT], BUFFER_SIZ))
    return 15;

  // bkp_to
  TCHAR bkp_name[BUFFER_SIZ];
  if (copy_to_pczztchar(bkp_name, argv[ARG_BKP_NAME], BUFFER_SIZ))
    return 15;

  // move_from
  TCHAR move_from[BUFFER_SIZ];
  if (copy_to_pczztchar(move_from, argv[ARG_MOVE_FROM], BUFFER_SIZ))
    return 15;

  // move_to
  TCHAR move_to[BUFFER_SIZ];
  if (copy_to_pczztchar(move_to, argv[ARG_MOVE_TO], BUFFER_SIZ))
    return 15;


  // =====================
  // first, make a backup of existing installation if needed.

  SHFILEOPSTRUCT shbkp;
  shbkp.hwnd = NULL;
  shbkp.wFunc = (bkp_name[0] == '\0' ? FO_DELETE : FO_MOVE);
  shbkp.pFrom = bkp_what;
  shbkp.pTo = bkp_name;
  shbkp.fFlags = FOF_NOCONFIRMATION|FOF_NOCONFIRMMKDIR;
  shbkp.lpszProgressTitle = "";

  fprintf(stderr, "Backing up %s to %s ...\n", argv[ARG_BKP_WHAT], argv[ARG_BKP_NAME]);
  int resbkp = SHFileOperation(&shbkp);
  if (resbkp != 0) {
    fprintf(stderr, "Error backing up %s to %s\n", argv[ARG_BKP_WHAT], argv[ARG_BKP_NAME]);
    cleanup_from(argv[ARG_MOVE_FROM]);
    pause();
    return 1;
  }


  // =====================
  // then, install the new files to their final location.

  SHFILEOPSTRUCT sh;
  sh.hwnd = NULL;
  sh.wFunc = FO_MOVE;
  sh.pFrom = move_from;
  sh.pTo = move_to;
  sh.fFlags = FOF_NOCONFIRMATION|FOF_NOCONFIRMMKDIR;
  sh.lpszProgressTitle = "";

  fprintf(stderr, "Renaming %s to %s ...\n", argv[ARG_MOVE_FROM], argv[ARG_MOVE_TO]);
  int res = SHFileOperation(&sh);
  if (res != 0) {
    fprintf(stderr, "Error renaming %s to %s\n", argv[ARG_MOVE_FROM], argv[ARG_MOVE_TO]);
    cleanup_from(argv[ARG_MOVE_FROM]);
    failure_restore_backup(bkp_what, bkp_name, argv[ARG_BKP_WHAT], argv[ARG_BKP_NAME]);
    pause();
    return 2;
  }


  // =====================
  // finally, remove empty dir containing the move_from source.

  int retcleanup = cleanup_from(argv[ARG_MOVE_FROM]);
  if (retcleanup != 0)
    return retcleanup;


  // =====================
  // and delete the no-longer-needed backup.

  SHFILEOPSTRUCT shclnbkp;
  shclnbkp.hwnd = NULL;
  shclnbkp.wFunc = FO_DELETE;
  shclnbkp.pFrom = bkp_name;
  shclnbkp.pTo = NULL;
  shclnbkp.fFlags = FOF_NOCONFIRMATION|FOF_NOCONFIRMMKDIR;
  shclnbkp.lpszProgressTitle = "";

  fprintf(stderr, "Cleaning up backup %s ...\n", argv[ARG_BKP_NAME]);
  int resclnbkp = SHFileOperation(&shclnbkp);
  if (resclnbkp != 0) {
    fprintf(stderr, "WARNING: Error cleaning up backup %s: error code %d\n", argv[ARG_BKP_NAME], resclnbkp);
    // ok, not quite an error, so proceed to return 0.
  }


  // =====================
  // all ok.

  fprintf(stderr, "done.");

  return 0;
}

