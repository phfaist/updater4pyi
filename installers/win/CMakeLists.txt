
cmake_minimum_required(VERSION 2.4)
project(do_install)

set(CMAKE_BUILD_TYPE "Release" CACHE STRING "Set the release type.")


add_executable(manage_install instmanager_win.cxx instcommon.cxx)
add_executable(do_install installer_win.cxx instcommon.cxx)

# strip the executables
get_target_property(manage_install_location  manage_install  LOCATION)
add_custom_command(TARGET manage_install  POST_BUILD
  COMMAND   "${CMAKE_STRIP}" "${manage_install_location}"
  )

get_target_property(do_install_location  do_install  LOCATION)
add_custom_command(TARGET do_install  POST_BUILD
  COMMAND   "${CMAKE_STRIP}" "${do_install_location}"
  )



# some time in the future, support cmake-based zip file generation.
# for now, you should do that manually.
# create a zip file named do_install.exe.zip containing at its root do_install.exe,
# manage_install.exe and its dependencies (e.g. libgcc_s_dw2-1.dll)


#
#set(zip_dep_files
#  # additional runtime dependencies of do_install.exe to include in zip file
#  libgcc_s_dw2-1.dll
#  # .. add more dependencies here
#  )
#
#
#set(CMAKE_INSTALL_PREFIX "" CACHE STRING "Installation prefix; for cpack")
#
#install(TARGETS do_install
#  RUNTIME DESTINATION ""
#  LIBRARY DESTINATION ""
#  )
#install(FILES ${zip_dep_files}
#  DESTINATION ""
#  )
#
#set(CPACK_GENERATOR "ZIP")
#set(CPACK_PACKAGE_FILE_NAME "do_install.exe.")
#
#
# .............. or ..........
#
## create the ZIP archive
#FIND_PROGRAM(ZIP_EXECUTABLE 7z PATHS "$ENV{ProgramFiles}/7-Zip") 
#IF(ZIP_EXECUTABLE)
#  SET(ZIP_COMMAND "\"${ZIP_EXECUTABLE}\" a -tzip \"<ARCHIVE>\" @<FILELIST>")
#ENDIF(ZIP_EXECUTABLE)
