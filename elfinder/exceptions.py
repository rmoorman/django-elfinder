""" elfinder Exceptions. """

class InvalidTarget(Exception):
    """ Raised when client requested an invalid File or Directory hash. 

        Invalid means it does not exist, or does not belong to the current
        tree.
    """
    pass
