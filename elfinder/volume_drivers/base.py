

class BaseVolumeDriver(object):
    def __init__(self, *args, **kwargs):
        pass

    def get_volume_id(self):
        """ Returns the volume ID for the volume, which is used as a prefix
            for client hashes.
        """
        raise NotImplementedError

    def get_info(self, target):
        """ Returns a dict containing information about the target directory
            or file. This data is used in response to 'open' commands to
            populates the 'cwd' response var.

            :param target: The hash of the directory for which we want info.
            If this is '', return information about the root directory.
            :returns: dict -- A dict describing the directory.
        """
        raise NotImplementedError

    def get_tree(self, target, ancestors=False, siblings=False):
        """ Gets a list of dicts describing children/ancestors/siblings of the
            target.

            :param target: The hash of the directory the tree starts from.
            :param ancestors: Include ancestors of the target.
            :param siblings: Include siblings of the target.
            :param children: Include children of the target.
            :returns: list -- a list of dicts describing directories.
        """
        raise NotImplementedError

    def read_file_view(self, request, hash):
        """ Django view function, used to display files in response to the
            'file' command.

            :param request: The original HTTP request.
            :param hash: The hash of the target file.
            :returns: dict -- a dict describing the new directory.
        """
        raise NotImplementedError

    def mkdir(self, name, parent):
        """ Creates a directory.

            :param name: The name of the new directory.
            :param parent: The hash of the parent directory.
            :returns: dict -- a dict describing the new directory.
        """
        raise NotImplementedError

    def mkfile(self, name, parent):
        """ Creates a directory.

            :param name: The name of the new file.
            :param parent: The hash of the parent directory.
            :returns: dict -- a dict describing the new file.
        """
        raise NotImplementedError
