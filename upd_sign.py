
# -*- coding: utf-8 -*-



class UpdateSignatureVerifyer(object):
    def __init__(self):
        pass

    def verify(self, update_info, fn):
        raise NotImplementedError




class UpdateNoSignatureVerifyer(UpdateSignatureVerifyer):
    def verify(self, update_info, fn):
        return True

