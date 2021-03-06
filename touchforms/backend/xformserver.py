import sys
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn
import threading
import logging
import xformplayer
import os
import java.lang
import time

from setup import init_classpath
init_classpath()
import com.xhaus.jyson.JysonCodec as json

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

DEFAULT_PORT = 4444

SIMULATED_DELAY = 0 #ms

class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class XFormHTTPGateway(threading.Thread):
    def __init__(self, port, extensions=[]):
        threading.Thread.__init__(self)
        self.server = ThreadingHTTPServer(('', port), XFormRequestHandler)
        self.server.extensions = extensions

    def run(self):
        self.server.serve_forever()

    def terminate(self):
        self.server.shutdown()

class XFormRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        delay()

        if 'content-length' in self.headers.dict:
            length = int(self.headers.dict['content-length'])
        else:
            logging.warn('content length required')
            self.send_error(400, 'content length required for post')
            return

        if 'content-type' not in self.headers.dict or self.headers.dict['content-type'] != 'text/json':
            logging.warn('content type missing or non-json')

        body = self.rfile.read(length)
        try:
            logging.debug('received: [%s]' % body)
            data_in = json.loads(body)
        except:
            logging.warn('content does not parse')
            self.send_error(400, 'content does not parse as valid json')
            return

        try:
            data_out = handle_request(data_in, extensions=self.server.extensions)
        except (Exception, java.lang.Exception), e:
            if isinstance(e, java.lang.Exception):
                e.printStackTrace() #todo: log the java stacktrace
            logging.exception('error handling request')
            self.send_error(500, 'internal error handling request: %s: %s' % (type(e), str(e)))
            return

        reply = json.dumps(data_out)

        logging.debug('returned: [%s]' % reply)
        delay()

        self.send_response(200)
        self.send_header('Content-Type', 'text/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(reply.encode('utf-8'))

def handle_request (content, **kwargs):
    if 'action' not in content:
        return {'error': 'action required'}

    action = content['action']
    nav_mode = content.get('nav', 'prompt')
    try:
        if action == 'new-form':
            if 'form-name' not in content:
                return {'error': 'form identifier required'}
            preload_data = content["preloader-data"] if "preloader-data" in content else {}
            return xformplayer.open_form(content['form-name'], content.get('instance-content'), kwargs.get('extensions', []), preload_data, nav_mode)

        elif action == 'edit-form':
            return {'error': 'unsupported'}

        elif action == 'answer':
            if 'session-id' not in content:
                return {'error': 'session id required'}
            if 'answer' not in content:
                return {'error': 'answer required'}

            return xformplayer.answer_question(content['session-id'], content['answer'], content.get('ix'))

        #sequential (old-style) repeats only
        elif action == 'add-repeat':
            if 'session-id' not in content:
                return {'error': 'session id required'}

            return xformplayer.new_repetition(content['session-id'])

        elif action == 'next':
            if 'session-id' not in content:
                return {'error': 'session id required'}

            return xformplayer.skip_next(content['session-id'])

        elif action == 'back':
            if 'session-id' not in content:
                return {'error': 'session id required'}

            return xformplayer.go_back(content['session-id'])

        elif action == 'edit-repeat':
            if 'session-id' not in content:
                return {'error': 'session id required'}
            if 'ix' not in content:
                return {'error': 'repeat index required'}

            return xformplayer.edit_repeat(content['session-id'], content['ix'])

        elif action == 'new-repeat':
            if 'session-id' not in content:
                return {'error': 'session id required'}

            return xformplayer.new_repeat(content['session-id'], content.get('ix'))
    
        elif action == 'delete-repeat':
            if 'session-id' not in content:
                return {'error': 'session id required'}
            if 'ix' not in content:
                return {'error': 'repeat index required'}

            return xformplayer.delete_repeat(content['session-id'], content['ix'], content.get('form_ix'))

        elif action == 'submit-all':
            if 'session-id' not in content:
                return {'error': 'session id required'}
            
            return xformplayer.submit_form(content['session-id'], content.get('answers', []), content.get('prevalidated', False))

        elif action == 'purge-stale':
            if 'window' not in content:
                return {'error': 'staleness window required'}

            return xformplayer.purge(content['window'])

        else:
            return {'error': 'unrecognized action'}
    
    except xformplayer.NoSuchSession:
        return {'error': 'invalid session id'}
    except xformplayer.SequencingException:
        return {'error': 'session is locked by another request'}

def delay():
    time.sleep(.5 * SIMULATED_DELAY / 1000)

if __name__ == "__main__":

    try:
        port = int(sys.argv[1])
    except IndexError:
        port = DEFAULT_PORT

    extension_modules = sys.argv[2:]

    gw = XFormHTTPGateway(port, extension_modules)
    gw.start()
    logging.info('started server on port %d' % port)

    try:
        while True:
            time.sleep(.01) #yield thread
    except KeyboardInterrupt:
        #note: the keyboardinterrupt event doesn't seem to be triggered in
        #jython, nor does jython2.5 support the httpserver 'shutdown' method
        logging.info('interrupted; shutting down...')
        gw.terminate()
