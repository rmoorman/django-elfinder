from django.core.exceptions import ObjectDoesNotExist
from elfinder.models import FileCollection, Directory, File
from elfinder.exceptions import InvalidTarget
import logging

""" Connector class for Django/elFinder integration.

    TODO 

    Create abstract Volume class so multiple volume types are possible. 
    Implement the current code as ModelVolume.
    
    Permissions checks when viewing/modifying objects - users can currently
    create files in other people's file collections, or delete files they
    do not own. This needs to be implemented in an extendable way, rather
    than being tied to one method of permissions checking.
"""


logger = logging.getLogger(__name__)


class connector():
    _version = '2.0'

    # _commands maps command names (specified by the client) to functions on
    # this class. Each command is tuple containing the function name and
    # an object representing which GET variables must/must not be set for
    # this command. Used by _check_command_variables.
    _commands = {'open': ('__open', {'target': True}),
                 'tree': ('__tree', {'target': True}),
                 'file': ('__file', {'target': True}),
                 'parents': ('__parents', {'target': True}),
                 'mkdir': ('__mkdir', {'target': True, 'name': True}),
                 'mkfile': ('__mkfile', {'target': True, 'name': True}),
                }

    httpAllowedParameters = ('cmd', 'target', 'targets[]', 'current', 'tree',
                             'name', 'content', 'src', 'dst', 'cut', 'init',
                             'type', 'width', 'height', 'upload[]')

    def __init__(self, collection, options, read_file_view=None, volumes={}):
        self.collection = collection
        self.options = options
        self.httpResponse = {}
        self.httpStatusCode = 200
        self.httpHeader = {'Content-type': 'application/json'}
        self._GET = {}
        self._response = {}
        self.return_view = None
        self.volumes = volumes

        # Use the default read_file view if one has not been specified.
        # It is imported here to prevent circular imports.
        if read_file_view == None:
            from elfinder.views import read_file
            self.read_file_view = read_file_view
            self.read_file_view = read_file

    def _get_object_by_hash(self, hash):
        """ Returns the object specified by the given hash.

            The hash is in the format "xn", where
            x is a letter identifying the type of object being requested and
            n is that object's id.

            d:  Directory
            f:  File

            The tree_id of the root node of the currently open FileCollection
            is checked to ensure the target belongs to that tree.
            The client requests the last-remembered dir on init, which breaks 
            things if they are now looking at a different FileCollection.

            If the target does not belong to the current tree, return the root
            of the current tree instead.
        """
        volume_id, target = hash.split('_')

        if target == '':
            # No target has been specified or the root dir is the target
            return self.collection.root_node, Directory

        try:
            object_id = int(target[1:])
        except ValueError:
            logger.error('Invalid target hash: %s' % target)
            raise Exception('Invalid target hash: %s' % target)

        current_tree_id = self.collection.root_node.tree_id

        if target[0] == 'f':
            model = File
            query = {'pk': object_id, 'parent__tree_id': current_tree_id}
        elif target[0] == 'd':
            model = Directory
            query = {'pk': object_id, 'tree_id': current_tree_id}
        else:
            raise Exception('Invalid target hash')

        try:
            object = model.objects.get(**query)
        except ObjectDoesNotExist:
            raise InvalidTarget('Could not open target')

        return object, model

    def _check_command_variables(self, command_variables):
        """ Checks the GET variables to ensure they are valid for this command.
            _commands controls which commands must or must not be set.

            This means command functions do not need to check for the presence
            of GET vars manually - they can assume that required items exist.
        """
        for field in command_variables:
            if command_variables[field] == True and field not in self._GET:
                return False
            elif command_variables[field] == False and field in self._GET:
                return False
        return True

    def _run_command(self, func_name, command_variables):
        """ Attempts to run the given command.

            If the command does not execute, or there are any problems
            validating the given _GET vars, an error message is set.

            func: the name of the function to run (e.g. __open)
            command_variables: a list of 'name':True/False tuples specifying
            which GET variables must be present or empty for this command.
        """
        if not self._check_command_variables(command_variables):
            self._response['error'] = 'Invalid arguments'
            return

        func = getattr(self, '_' + self.__class__.__name__ + func_name, None)
        if not callable(func):
            self._response['error'] = 'Command failed'
            return

        import traceback
        import sys
        try:
            func()
        except Exception, e:
            self._response['error'] = '%s' % e
            logger.exception(e)

    def run(self, request):
        """ Main entry point for running commands. Attemps to run a command
            function based on info in request.GET.

            The command function will complete in one of two ways. It can
            set _response, which will be turned in to an HttpResponse and
            returned to the client.

            Or it can set return_view, a Django View function which will
            be rendered and returned to the client.
        """

        self.request = request
        # Copy allowed parameters from the given request's GET to self._GET
        for field in self.httpAllowedParameters:
            if field in request.GET:
                if field == "targets[]":
                    self._GET[field] = request.GET.getlist(field)
                else:
                    self._GET[field] = request.GET[field]

        # If a valid command has been specified, try and run it. Otherwise set
        # the relevant error message.
        if 'cmd' in self._GET:
            if self._GET['cmd'] in self._commands:
                cmd = self._commands[self._GET['cmd']]
                self._run_command(cmd[0], cmd[1])
            else:
                self._response['error'] = 'Unknown command'
        else:
            self._response['error'] = 'No command specified'

        self.httpResponse = self._response
        return self.httpStatusCode, self.httpHeader, self.httpResponse

    def __parents(self):
        """ Handles the parent command.

            Sets _response['tree'], which contains a list of dicts representing
            the ancestors/siblings of the target object.

            The tree is not a tree in the traditional hierarchial sense, but
            rather a flat list of dicts which have hash and parent_hash (phash)
            values so the client can draw the tree.
        """
        object, model = self._get_object_by_hash(self._GET['target'])
        self._response['tree'] = object.get_tree(ancestors=True, siblings=True)

    def __tree(self):
        """ Handles the 'tree' command.

            Sets _response['tree'] - a list of children of the specified
            target Directory.
        """
        object, model = self._get_object_by_hash(self._GET['target'])
        self._response['tree'] = object.get_tree(children=True)

    def __file(self):
        """ Handles the 'file' command.

            Sets return_view, which will cause read_file_view to be rendered
            as the response. A custom read_file_view can be when initialising
            the connector.
        """
        object, model = self._get_object_by_hash(self._GET['target'])
        if model == File:
            # A file was requested, so return the read_file view.
            self.return_view = self.read_file_view(self.request, object,
                                                    self.collection)

    def __open(self):
        """ Handles the 'open' command.

            Sets _response['files'] and _response['cwd'].

            If 'tree' is requested, 'files' contains information about all
            ancestors, siblings and children of the target. Otherwise, 'files'
            only contains info about the target's immediate children.

            'cwd' contains info about the currently selected directory.
        """
        object, model = self._get_object_by_hash(self._GET['target'])

        self._response['cwd'] = object.get_info()

        if 'tree' in self._GET and self._GET['tree'] == '1':
            # Add info about ancestors, siblings and children
            self._response['files'] = object.get_tree(True, True, True)
            self._response['files'].append(object.get_info())
        else:
            # Add info about childen only
            self._response['files'] = object.get_tree(False, False, True)

        # If the request includes 'init', add some client initialisation
        # data to the response.
        if 'init' in self._GET:
            self._response['api'] = '2.0'
            self._response['disabled'] = []
            self._response['params'] = {'dotFiles': False,
                                           'uplMaxSize': '128M',
                                           'archives': [],
                                           'extract': [],
                                           'url': 'none'}

    def _create_object(self, model):
        """ Creates a directory or file.

            'model' is either Directory or File.
            The 'target' GET variable specifies the parent of the new object.
        """
        from django.core.exceptions import ValidationError

        try:
            parent, parent_model = self._get_object_by_hash(self._GET['target'])
        except Exception, e:
            self._response['error'] = 'Invalid parent directory'
            logger.exception(e)
            return

        name = self._GET['name'].replace('+', ' ')

        new_obj = model(name=name,
                        parent=parent,
                        collection=self.collection)
        
        try:
            new_obj.validate_unique()
        except ValidationError, e:
            self._response['error'] = " ".join(e.messages)
            logger.exception(e)
            return

        try:
            new_obj.save()
        except Exception, e:
            self._response['error'] = 'Could not create new object'
            logger.exception(e)

        # The client expects 'added' to be a list of new items.
        self._response['added'] = [new_obj.get_info()]

    def __mkdir(self):
        return self._create_object(Directory)

    def __mkfile(self):
        return self._create_object(File)
