
# -*- coding: utf-8 -*-


from upd_source import UpdateInfo, UpdateSource



class UpdateInterface(object):
    def __init__(self):
        pass

    def ask_to_install_update(self, update_info):
        """
        update_info is an `UpdateInfo` object
        """
        raise NotImplementedError
    
