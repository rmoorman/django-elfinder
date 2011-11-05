from django.test import TestCase
from django.core.urlresolvers import reverse
from elfinder.models import FileCollection, Directory, File
from elfinder.exceptions import InvalidTarget
import json
import logging


class elFinderTest(TestCase):
    """ Tests basic template functionality.
    """
    fixtures = ['testdata.json']

    def setUp(self):
        # Disable logging when running tests
        logging.disable(logging.CRITICAL)

    def test_elfinder_index(self):
        """ Ensures that the elfinder.html template is used, and coll_id is in
            the template's context.
        """
        self.collection = FileCollection.objects.get(pk=1)
        response = self.client.get(reverse('elfinder_index',
                                            args=[self.collection.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'elfinder.html')
        self.assertEqual(response.context['coll_id'], self.collection.id)


class elFinderCmdTest(TestCase):
    """ Base class for testing connector commands.

        Each command has its own class which extends this, and adds one
        or more specific tests for that command. This lets each command
        test valid and invalid requests.
    """
    fixtures = ['testdata.json']

    def setUp(self):
        # Disable logging when running tests
        logging.disable(logging.CRITICAL)
        self.collection = FileCollection.objects.get(pk=1)


    def get_command_response(self, variables={}):
        """ Helper function to issue commands to the connector.
        """
        return self.client.get(reverse('elfinder_connector',
                                        args=[self.collection.id]),
                                        variables)

    def get_json_response(self, variables={}, fail_on_error=True):
        """ Helper function - calls get_command_response and ensures the
            response is a JSON object. Adds the deserialised JSON object
            to the response.

            If fail_on_error is true and the response includes an 'error'
            object, the test will fail.
        """
        response = self.get_command_response(variables)
        response.json = json.loads(response.content)

        if fail_on_error:
            self.assertFalse('error' in response.json,
                'JSON Response contained an error: ' + response.content)
        return response


class elFinderUnknownCmd(elFinderCmdTest):
    def test_unknown_cmd(self):
        response = self.get_json_response({'cmd': 'invalid_cmd_test'}, False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Unknown command')


class elFinderOpenCmd(elFinderCmdTest):
    def test_invalid_args(self):
        vars = ({'cmd': 'open'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid arguments')

    def test_valid_open(self):
        vars = ({'cmd': 'open',
                 'target': self.collection.root_node.get_hash(),
                 'tree': 1})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_valid_open_with_init(self):
        vars = ({'cmd': 'open',
                 'target': self.collection.root_node.get_hash(),
                 'tree': 1,
                 'init': 1})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['api'], '2.0')


class elFinderMkdirCmd(elFinderCmdTest):
    def test_invalid_args(self):
        vars = ({'cmd': 'mkdir'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid arguments')

    def test_valid_mkdir(self):
        vars = ({'cmd': 'mkdir',
                 'target': self.collection.root_node.get_hash(),
                 'name': 'new dir'})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_invalid_target(self):
        response = self.get_json_response({'cmd': 'mkdir',
                                           'target': 'does-not-exist',
                                           'name': 'new dir'},
                                           fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid parent directory')

    def test_duplicate_dir_name(self):
        """ Try to create two dirs with the same name and ensure it fails.
        """
        vars = ({'cmd': 'mkdir',
                 'target': self.collection.root_node.get_hash(),
                 'name': 'dupe_dir_test'})
        response = self.get_json_response(vars)
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'],
                         'Directory with this Name and Parent already exists.')


class elFinderMkfileCmd(elFinderCmdTest):
    def test_invalid_args(self):
        vars = ({'cmd': 'mkdir'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Invalid arguments')

    def test_valid_mkfile(self):
        vars = ({'cmd': 'mkfile',
                 'target': self.collection.root_node.get_hash(),
                 'name': 'test file.txt'})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)

    def test_duplicate_filename(self):
        """ Try to create two files with the same name and ensure it fails.
        """
        vars = ({'cmd': 'mkfile',
                 'target': self.collection.root_node.get_hash(),
                 'name': 'dupe_filename_test'})
        response = self.get_json_response(vars)
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'],
                         'File with this Name and Parent already exists.')


class elFinderParentsCmd(elFinderCmdTest):
    def test_valid_parents(self):
        vars = ({'cmd': 'parents',
                 'target': self.collection.root_node.get_hash()})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)


class elFinderTreeCmd(elFinderCmdTest):
    def test_valid_tree(self):
        vars = ({'cmd': 'tree',
                 'target': self.collection.root_node.get_hash()})
        response = self.get_json_response(vars)
        self.assertEqual(response.status_code, 200)


class elFinderFileCmd(elFinderCmdTest):

    def setUp(self):
        super(elFinderFileCmd, self).setUp()
        self.file = File.objects.get(pk=1)

    def test_valid_file(self):
        vars = ({'cmd': 'file',
                 'target': self.file.get_hash()})
        response = self.get_command_response(vars)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'read_file.html')
        self.assertEqual(response.context['coll'], self.collection)
        self.assertEqual(response.context['file'], self.file)

    def test_invalid_file(self):
        vars = ({'cmd': 'file',
                 'target': 'fc1_f1234'})
        response = self.get_json_response(vars, fail_on_error=False)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['error'], 'Could not open target')
