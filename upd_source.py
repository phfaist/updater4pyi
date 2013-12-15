# -*- coding: utf-8 -*-



class UpdateInfo(object):
    def __init__(self, version=None, filename=None, url=None, signature=None, **kwargs):
        self.version = version
        self.filename = filename
        self.url = url
        self.signature = signature
        for k,v in kwargs.iteritems():
            setattr(self, k, v)

    def get_version(self):
        return self.version

    def get_filename(self):
        return self.filename

    def get_url(self):
        return self.url

    def get_signature(self):
        return self.signature;



class UpdateSource(object):
    def __init__(self):
        pass

    def check_for_update(self):
        """
        Should return an `UpdateInfo` object if an update is available, or `None` if not.
        """
        raise NotImplementedError
