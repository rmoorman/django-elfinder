from django.views.generic import TemplateView
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.utils import simplejson as json
from django.template import RequestContext
from elfinder.connector import connector
from elfinder.models import FileCollection


def index(request, coll_id):
    """ Displays the elFinder file browser template for the specified
        FileCollection.
    """
    collection = FileCollection.objects.get(pk=coll_id)
    return render_to_response("elfinder.html",
                              {'coll_id': collection.id},
                              RequestContext(request))


def connector_view(request, coll_id):
    """ Handles requests for the elFinder connector.
    """
    collection = FileCollection.objects.get(pk=coll_id)
    finder_opts = {}
    finder = connector(collection, finder_opts)
    finder.run(request)

    # Some commands (e.g. read file) will return a Django View - if it
    # is set, return it directly instead of building a response
    if finder.return_view:
        return finder.return_view

    ret = HttpResponse(mimetype=finder.httpHeader['Content-type'])

    if finder.httpHeader['Content-type'] == 'application/json':
        ret.content = json.dumps(finder.httpResponse)
    else:
        ret.content = finder.httpResponse
    ret.status_code = finder.httpStatusCode

    return ret


def read_file(request, file, collection):
    """ Default view for responding to "open file" requests.

        coll: FileCollection this File belongs to
        file: The requested File object
    """
    return render_to_response("read_file.html",
                              {'coll': collection,
                               'file': file},
                              RequestContext(request))
