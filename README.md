
UPDATER4PYI
===========

Updater4pyi is a simple, lightweight, flexible python library to enable your
applications packaged with pyinstaller to auto-update themselves.

Its design is extremely flexible, so it can work with various "sources", e.g. a
github repository, but you can write your own source just as easily.

The update process runs for both one-file and one-dir packaged applications, on
Windows, Linux and Mac OS X.

The base library is interface-independent. An interface in PyQt4 as well as one
for console applications are provided, but writing an interface for another GUI
system (wxWidgets ...) should be a matter of several lines of code.




Installation & Usage
====================

Updater4pyi is available on PyPI, so the recommended installation is through
there.

You will also need to install one hook for pyinstaller. If you have a custom
hook directory in your project, you can place the file named
`hook-updater4pyi.py` it there; otherwise, locate your pyinstaller `hooks`
directory and copy the file `hook-updater4pyi.py` in there.

To use updater4pyi in your programs, you need to:

  - describe where to look for updates (the *sources*)

  - instantiate the updater, giving it the corresponding sources

  - create an interface, which will interact with the user.

For example, the [bibolamazi project](https://github.com/phfaist/bibolamazi)
uses the updater4pyi framework, and the relevant lines in there are:

    from updater4pyi import upd_source, upd_core
    from updater4pyi.upd_iface_pyqt4 import UpdatePyQt4Interface

    swu_source = upd_source.UpdateGithubReleasesSource('phfaist/bibolamazi')
    swu_updater = upd_core.Updater(current_version=...,
                                   update_source=swu_source)
    swu_interface = UpdatePyQt4Interface(swu_updater,
                                         progname='Bibolamazi',
                                         ask_before_checking=True,
                                         parent=QApplication.instance())

Then, you need to make sure that pyinstaller can find updater4pyi, i.e. it has
to be in your python path.


Sources
=======

At the moment, there are only two source types

  - github releases. See upd_source.UpdateGithubReleasesSource. You can specify
    naming patterns as regexp's to match the release files with corresponding
    platforms

  - local directory source (used for debugging)


However, it is straightforward to write your own source. Look at `upd_source.py`
to get an idea. If you do so, it would be great to contribute it to updater4pyi
so that other people can profit!



Security
========

This library supports downloads through HTTPS with certificate verification,
making the download and update process secure. The default root certificate is
provided with this package, and can be changed to include your custom one if
needed.



Interfaces
==========

At the moment, there are the following interfaces for updates:

  - A simple console interface, running at each program start, that prompts the
    user to check for updates. Not very useful, more meant for debugging.

  - A full-featured abstract GUI generic interface. This interface does not
    depend on any GUI, and abstracts out tasks such as timing, saving settings
    and message boxes which need to be implemented by subclasses. This class is
    meant to be used as a base class to write updater interfaces for other GUI
    systems (wxWidgets, ...)

  - A PyQt4 interface is provided based on the generic GUI interface mentioned
    in the previous point.

