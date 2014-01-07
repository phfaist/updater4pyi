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
  ARG_BKP_NAME = 2,
  ARG_MOVE_FROM = 3,
  ARG_MOVE_TO = 4,
  // this one is equal to the reqested argc number:
  ARG_ONE_PAST_LAST
};


int main(int argc, char **argv)
{
  if (argc != ARG_ONE_PAST_LAST) {
    fprintf(stderr,
            "Usage: %s  <backup-what> <backup-name> <move-from> <move-to>\n",
            argv[0]);
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
    return 2;
  }

  // =====================
  // finally, remove empty dir containing the move_from source.

  char move_from_cpy[BUFFER_SIZ];
  if (strlen(argv[ARG_MOVE_FROM]) >= BUFFER_SIZ)
    return 15;
  strcpy(move_from_cpy, argv[ARG_MOVE_FROM]);
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

  // =====================
  // all ok.

  fprintf(stderr, "done.");

  return 0;
}


// solution inspired by http://www.catch22.net/tuts/self-deleting-executables

BOOL SelfDelete(TCHAR *szPath)
{
  if (szPath[0] == '\0')
    return TRUE;

  TCHAR szCmd[BUFFER_SIZ+50];

  lstrcpy(szCmd, "/c sleep 2 & rmdir /s /q ");
  lstrcat(szCmd, szPath);
  lstrcat(szCmd, " >> NUL");

  TCHAR comspecFile[BUFFER_SIZ];

  if((GetEnvironmentVariable("ComSpec",comspecFile,BUFFER_SIZ)!=0) &&
     ((INT)ShellExecute(0,0,comspecFile,szCmd,0,SW_HIDE)>32))
    return TRUE;

  return FALSE;
}
