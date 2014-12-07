
Quick Start
-----------

Simple example: say you want to add an auto-update feature to your python/PyQt4 program,
hosted on github. Add the following lines into your python program::
    
    from updater4pyi import upd_source, upd_core
    from updater4pyi.upd_iface_pyqt4 import UpdatePyQt4Interface
    
    swu_source = upd_source.UpdateGithubReleasesSource('githubusername/githubproject')
    swu_updater = upd_core.Updater(current_version=...,
                                   update_source=swu_source)
    swu_interface = UpdatePyQt4Interface(swu_updater,
                                         progname='Your Project Name',
                                         ask_before_checking=True,
                                         parent=QApplication.instance())


You should also add the hook `hook-updater4pyi.py` into your PyInstaller hooks path
(presumably into your custom hooks). Then your PyInstaller-packaged program will ask the
user if they agree to auto-update, then regularly check for updates and ask to install
them. You may need to fiddle a bit with the naming patterns of your releases (specify a
second argument to the `UpdateGithubReleasesSource` constructor).

The library is designed to be highly flexible. It should be easy to write update sources
for any other type of sources, such as XML application feeds etc. Likewise, the library
does *not* rely on PyQt4 (it just provides a convenient interface for those PyQt4
apps). It should be simple to write an interface in whater Gui toolkit you prefer--see
:py:class:`upd_iface.UpdateGenericGuiInterface`.


Structure of Updater4pyi
------------------------


* the core :py:class:`upd_core.Updater` class takes care of actually checking and
  installing updates.

* a :py:class:`upd_iface.UpdateInterface` subclass takes care of interacting with the
  user and scheduling checks for available updates. See
  :py:class:`upd_iface_pyqt4.UpdatePyQt4Interface` for example.

* an :py:class:`upd_source.UpdateSource` subclass is configured to know where and how to
  query for available updates. See :py:class:`upd_source.UpdateGithubReleasesSource` for
  example.
