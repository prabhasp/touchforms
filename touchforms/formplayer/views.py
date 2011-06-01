from django.shortcuts import get_object_or_404
from django.conf import settings
from touchforms.formplayer.models import XForm, PlaySession
from touchforms.formplayer.const import *
from touchforms.formplayer.autocomplete import autocompletion, DEFAULT_NUM_SUGGESTIONS
from django.http import HttpResponseRedirect, HttpResponse,\
    HttpResponseServerError, HttpRequest
from django.core.urlresolvers import reverse
import logging
import httplib
from urlparse import urlparse
import traceback
import sys
from django.views.decorators.http import require_POST
import json
from collections import defaultdict
from StringIO import StringIO
from touchforms.formplayer.signals import xform_received
from django.template.context import RequestContext
from django.shortcuts import render_to_response
import tempfile
import os

def xform_list(request):
    forms_by_namespace = defaultdict(list)
    success = True
    notice = ""
    if request.method == "POST":
        if "file" in request.FILES:
            file = request.FILES["file"]
            try:
                tmp_file_handle, tmp_file_path = tempfile.mkstemp()
                tmp_file = os.fdopen(tmp_file_handle, 'w')
                tmp_file.write(file.read())
                tmp_file.close()
                new_form = XForm.from_file(tmp_file_path, str(file))
                notice = "Created form: %s " % file
            except Exception, e:
                logging.error("Problem creating xform from %s: %s" % (file, e))
                success = False
                notice = "Problem creating xform from %s: %s" % (file, e)
        else:
            success = False
            notice = "No uploaded file set."
            
            
            
    for form in XForm.objects.all():
        forms_by_namespace[form.namespace].append(form)
    return render_to_response("formplayer/xform_list.html", 
                              {'forms_by_namespace': dict(forms_by_namespace),
                               "success": success,
                               "notice": notice},
                               
                              context_instance=RequestContext(request))
                              

def download(request, xform_id):
    """
    Download an xform
    """
    xform = get_object_or_404(XForm, id=xform_id)
    response = HttpResponse(mimetype='application/xml')
    response.write(xform.file.read()) 
    return response


def playkb(request, xform_id, callback=None, preloader_data={}):
    return play(request, xform_id, callback, preloader_data, inputmode='type')

def play(request, xform_id, callback=None, preloader_data={}, inputmode='touch'):
    """
    Play an XForm.
    
    If you specify callback, instead of returning a response this view
    will call back to your method upon completion (POST).  This allows
    you to call the view from your own view, but specify a callback
    method afterwards to do custom processing and responding.
    
    The callback method should have the following signature:
        response = <method>(xform, document)
    where:
        xform = the django model of the form 
        document = the couch object created by the instance data
        response = a valid http response
    """
    xform = get_object_or_404(XForm, id=xform_id)
    instance = None
    if request.method == "POST":
        if request.POST["type"] == 'form-complete':
            # get the instance
            instance = request.POST["output"]

            # raise signal
            xform_received.send(sender="player", instance=instance)
        elif request.POST["type"] == 'form-aborted':
            return HttpResponseRedirect("/")
        # call the callback, if there, otherwise route back to the 
        # formplayer list
    if callback and instance is not None:
        return callback(xform, instance)
    elif instance is not None:
        response = HttpResponse(mimetype='application/xml')
        response.write(instance)
        return response
    
    preloader_data_js = json.dumps(preloader_data)
    templ = {
        'touch': 'touchforms/touchscreen.html',
        'type': 'typeforms.html',
    }[inputmode]
    return render_to_response(templ, {
            "form": xform,
            "mode": 'xform',
            "preloader_data": preloader_data_js,
            "dim": get_player_dimensions(request),
            "fullscreen": request.GET.get('mode', '').startswith('full')
        }, context_instance=RequestContext(request))

def play_remote(request, session_id=None):
    if not session_id:
        xform = request.POST.get('xform')
        try:
            tmp_file_handle, tmp_file_path = tempfile.mkstemp()
            tmp_file = os.fdopen(tmp_file_handle, 'w')
            tmp_file.write(xform.encode('utf-8'))
            tmp_file.close()
            new_form = XForm.from_file(tmp_file_path, str(file))
            notice = "Created form: %s " % file
        except Exception, e:
            logging.error("Problem creating xform from %s: %s" % (file, e))
            success = False
            notice = "Problem creating xform from %s: %s" % (file, e)
            raise e
        session = PlaySession(
            next = request.POST.get('next'),
            data = json.loads(request.POST.get('data')),
            xform_id = new_form.id,
        )
        session.save()
        return HttpResponseRedirect(reverse('xform_play_remote', args=[session._id]))

    session = PlaySession.get(session_id)

    if request.method == "POST":
        def callback(xform, instance):
            next = session.next
            xform.delete()
            session.delete()
            return HttpResponseRedirect(session.next)
    else:
        callback = None
    return play(request, session.xform_id, callback, session.data)

def get_player_dimensions(request):
    def get_dim(getparam, settingname):
        dim = request.GET.get(getparam)
        if not dim:
            try:
                dim = getattr(settings, settingname)
            except AttributeError:
                pass
        return dim

    return {
        'width': get_dim('w', 'TOUCHSCREEN_WIDTH'),
        'height': get_dim('h', 'TOUCHSCREEN_HEIGHT')
    }

def player_proxy(request):
    """Proxy to an xform player, to avoid cross-site scripting issues"""
    data = request.raw_post_data if request.method == "POST" else None
    response = _post_data(data, settings.XFORMS_PLAYER_URL, content_type="text/json")
    return HttpResponse(response)

def _post_data(data, url, content_type):
    up = urlparse(url)
    headers = {}
    headers["content-type"] = content_type
    headers["content-length"] = len(data)
    conn = httplib.HTTPConnection(up.netloc)
    conn.request('POST', up.path, data, headers)
    resp = conn.getresponse()
    results = resp.read()
    return results
    
def api_preload_provider(request):
    param = request.GET.get('param', "")
    param = param.strip().lower()

    value = param
    if param == PRELOADER_TAG_UID:
        import uuid
        value = uuid.uuid4().hex

    return HttpResponse(value)

def api_autocomplete(request):
    domain = request.GET.get('domain')
    key = request.GET.get('key', '')
    max_results = int(request.GET.get('max', str(DEFAULT_NUM_SUGGESTIONS)))

    return HttpResponse(json.dumps(autocompletion(domain, key, max_results)), 'text/json')

def player_abort(request):
    class TimeoutException(Exception):
        pass

    try:
        raise TimeoutException("A touchscreen view has timed out and was aborted")
    except TimeoutException:
        logging.exception('')

    try:
        redirect_to = reverse(settings.TOUCHFORMS_ABORT_DEST)
    except AttributeError:
        redirect_to = '/'

    return HttpResponseRedirect(redirect_to)
