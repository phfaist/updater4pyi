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


#define BUFFER_SIZ 2048

BOOL add_quoted_parameter(TCHAR *dest, TCHAR *p, size_t maxsiz);
int cleanupself(TCHAR *self_temp_dir, char *argv_self_tmp_dir);
BOOL SelfDelete(TCHAR *szPath);

enum {
  ARG_WAIT_PID = 1,
  ARG_NEED_SUDO,
  ARG_BKP_WHAT,
  ARG_BKP_NAME,
  ARG_MOVE_FROM,
  ARG_MOVE_TO,
  ARG_SELF_TEMP_DIR,
  ARG_RELAUNCH_AFTER,
  // this one is equal to the reqested argc number:
  ARG_ONE_PAST_LAST
};

int do_main(int argc, char **argv);


int main(int argc, char **argv)
{
  if (argc != ARG_ONE_PAST_LAST) {
    fprintf(stderr,
            "Usage: %s  <wait-pid> <need-sudo> <backup-what> <backup-name>"
            " <move-from> <move-to> <rm-temp-do_install-dir> <relaunch-after>\n",
            argv[0]);
    pause();
    return 100;
  }

  // self_temp_dir
  TCHAR self_temp_dir[BUFFER_SIZ];
  if (copy_to_pczztchar(self_temp_dir, argv[ARG_SELF_TEMP_DIR], BUFFER_SIZ))
    return 15;

  int retcode = do_main(argc, argv);

  cleanupself(self_temp_dir, argv[ARG_SELF_TEMP_DIR]);

  return retcode;
}

int do_main(int argc, char **argv)
{

  // wait_pid
  DWORD wait_pid = atoi(argv[ARG_WAIT_PID]);

  // need_sudo
  BOOL need_sudo = atoi(argv[ARG_NEED_SUDO]) ? TRUE: FALSE;

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

  TCHAR relaunch_after[BUFFER_SIZ];
  if (copy_to_pczztchar(relaunch_after, argv[ARG_RELAUNCH_AFTER], BUFFER_SIZ))
    return 15;


  // =====================
  // first, wait for the given process.

  if (wait_pid != 0) {
    fprintf(stderr, "Waiting for process %d to finish ...\n", wait_pid);
    HANDLE hProcWait = OpenProcess(SYNCHRONIZE, false, wait_pid);
    if (hProcWait != NULL) {
      DWORD waitret = WaitForSingleObject(hProcWait, INFINITE);
      CloseHandle(hProcWait);
      if (waitret != WAIT_OBJECT_0) {
        fprintf(stderr, "Error waiting for process %d to finish: code %d\n", wait_pid, waitret);
        pause();
        return 16;
      }
    }
  }

  // make sure resources are freed out
  Sleep(1000);

  // =====================
  // now, run the actual installer, possibly with administrator priviledges.

  char thisexe[BUFFER_SIZ];
  char do_install_exe[BUFFER_SIZ];
  TCHAR t_do_install_exe[BUFFER_SIZ];
  TCHAR doinst_parameters[4*BUFFER_SIZ];

  if (strlen(argv[0]) >= BUFFER_SIZ)
    return 15;
  strcpy(thisexe, argv[0]);
  char *dname = dirname(thisexe);

  if (strlen(dname) >= BUFFER_SIZ)
    return 15;
  strcpy(do_install_exe, dname);
  if (strlen("\\")+strlen(do_install_exe) >= BUFFER_SIZ)
    return 15;
  strcat(do_install_exe, "\\");
  if (strlen("do_install.exe")+strlen(do_install_exe) >= BUFFER_SIZ)
    return 15;
  strcat(do_install_exe, "do_install.exe");

  if (copy_to_pczztchar(t_do_install_exe, do_install_exe, BUFFER_SIZ))
    return 15;

  if (!add_quoted_parameter(doinst_parameters, bkp_what, BUFFER_SIZ))
    return 15;
  if (!add_quoted_parameter(doinst_parameters, bkp_name, BUFFER_SIZ))
    return 15;
  if (!add_quoted_parameter(doinst_parameters, move_from, BUFFER_SIZ))
    return 15;
  if (!add_quoted_parameter(doinst_parameters, move_to, BUFFER_SIZ))
    return 15;

  SHELLEXECUTEINFO doinstsh;
  doinstsh.cbSize = sizeof(SHELLEXECUTEINFO);
  doinstsh.fMask = SEE_MASK_NOCLOSEPROCESS;
  doinstsh.hwnd = NULL;
  doinstsh.lpVerb = need_sudo ? "runas" : "open";
  doinstsh.lpFile = t_do_install_exe;
  doinstsh.lpParameters = doinst_parameters;
  doinstsh.lpDirectory = NULL;
  doinstsh.nShow = SW_SHOW;
  doinstsh.hInstApp = NULL;

  fprintf(stderr, "Executing %s ...\n", do_install_exe);
  BOOL doinst_ok = ShellExecuteEx(&doinstsh);
  if (!doinst_ok) {
    fprintf(stderr, "Error executing %s\n", do_install_exe);
    pause();
    return 31;
  }

  fprintf(stderr, "Waiting for do_install.exe process to finish...\n");
  DWORD doinstwaitret = WaitForSingleObject(doinstsh.hProcess, INFINITE);
  DWORD doinstret;
  int doinstgret = GetExitCodeProcess(doinstsh.hProcess, &doinstret);
  CloseHandle(doinstsh.hProcess);

  if (doinstwaitret != WAIT_OBJECT_0) {
    fprintf(stderr, "Error waiting for do_install.exe process to finish: error code %d\n", doinstwaitret);
    pause();
    return 17;
  }
  if (!doinstgret) {
    fprintf(stderr, "Error: can't get do_install.exe return code\n");
    pause();
    return 18;
  }
  if (doinstret != 0) {
    fprintf(stderr, "Error: do_install.exe returned error code %d. Install failed.\n", doinstret);
    pause();
    // but still proceed to relaunch the program and autodestruct.
    //return doinstret;
  }


  // =====================
  // now, relaunch the new version of the program.

  fprintf(stderr, "Relaunching program %s ...\n", argv[ARG_RELAUNCH_AFTER]);
  int relaunch_ret = (int)ShellExecute(NULL, "open", relaunch_after, NULL, NULL, SW_SHOW);
  if (relaunch_ret <= 32) {
    fprintf(stderr, "Error relaunching program %s!\n", argv[ARG_RELAUNCH_AFTER]);
    return 32;
  }

  // =====================
  // all ok.

  return 0;
}

BOOL add_quoted_parameter(TCHAR *dest, TCHAR *p, size_t maxsiz)
{
  int k = lstrlen(dest);
  if (k >= maxsiz-2)
    return FALSE;

  // start with a space if we need to separate with previous content
  if (k > 0)
    dest[k++] = ' ';

  // open quote
  dest[k++] = '"';

  while (k < maxsiz-2 && *p != '\0') {
    dest[k++] = *p;
    if (*p == '"')
      dest[k++] = '"'; // repeat the double-quote to escape it in windows command parameter

    ++p;
  }
  if (k >= maxsiz-2)
    return FALSE;

  dest[k++] = '"'; // close quote
  dest[k] = '\0';
  return TRUE;
}


int cleanupself(TCHAR *self_temp_dir, char *argv_self_temp_dir)
{
  // finally, autodestruct and return.

  fprintf(stderr, "Autodestructing %s ...\n", argv_self_temp_dir);
  return SelfDelete(self_temp_dir) ? 0 : 3;
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
