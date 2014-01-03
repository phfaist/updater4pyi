
# hook for pyinstaller

import updater4pyi
import os.path

def locpath(x):
    return os.path.join(os.path.dirname(updater4pyi.__file__), x)

datas = [
    (locpath('cacert.pem'), 'updater4pyi'),
    (locpath('installers/unix/'), 'updater4pyi/installers/unix')
    ];

#from hookutils import collect_data_files
#datas = collect_data_files('updater4pyi')
#print "DATAS IS\n\t%r"%(datas)
