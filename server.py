#! /usr/bin/python

#######################################
#
#  Python Proxy Server
# 
#  Author: Tanghong Qiu
#  E-mail: taqiu@gmail.com
#    Date: Apr 6, 2014
#
#######################################

__version__ = '1.0'

import time
import BaseHTTPServer
import SocketServer
import socket
import select
import urlparse
import ssl
import argparse
 

class Config:
    def __init__(self):
        self.host = ''
        self.port = 50000
        self.timeout= 60
        self.buflen = 8192
        self.white_list = {}
        self.ssl_off = False
        self.server_key = 'auth/server.key'
        self.server_crt = 'auth/server.crt'
        self.ca_crt = 'auth/server.crt'

config = Config()


class ProxyHandler (BaseHTTPServer.BaseHTTPRequestHandler):

    def setup(self):
        self.__class__.setup = BaseHTTPServer.BaseHTTPRequestHandler.setup
        self.__class__.do_PUT = self.__class__.do_GET
        self.__class__.do_POST = self.__class__.do_GET
        self.__class__.do_HEAD = self.__class__.do_GET
        self.__class__.do_DELETE = self.__class__.do_GET
        self.__class__.do_OPTIONS = self.__class__.do_GET
        self.setup()


    def handle(self):
        self.__class__.handle = BaseHTTPServer.BaseHTTPRequestHandler.handle 
        (ip, port) =  self.client_address
        print 'request from %s' % ip
        if len(config.white_list) > 0 and ip not in config.white_list:
            self.send_error(403) 
            self.wfile.write('Your ip [%s] is not in white list' % ip)
        else:
            self.handle()


    def finish(self):
        self.connection.close()


    def _connect_target(self, host):
        i = host.find(':')
        if i > -1:
            host, port = host[:i], int(host[i+1:])
        else:
            port = 80

#        print "connect to %s:%d" % (host, port)
        self.target.connect((host, port))


    def do_CONNECT(self):
        self.target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._connect_target(self.path)
            self.send_response(200, 'Connection established')
            self.send_header("Proxy-agent", "SimpleAnonymizer %s" % __version__)
            self.end_headers()
            self._read_write(timeout=300)
        except Exception as e:
            self.send_error(404, str(e))
        finally:
            self.target.close()


    def do_GET(self):
        (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(
            self.path, 'http')
        if scheme != 'http' or fragment or not netloc:
            self.send_error(400, "bad url %s" % self.path)
            return
        self.target = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._connect_target(netloc)
            self.log_request()
            self.target.send("%s %s %s\r\n" % (self.command,
                                       urlparse.urlunparse(('', '', path,
                                                            params, query,
                                                           '')),
                                                           self.request_version))
            self.headers['Connection'] = 'close'
            del self.headers['Proxy-Connection']
            for key_val in self.headers.items():
                self.target.send("%s: %s\r\n" % key_val)
            self.target.send("\r\n")
            self._read_write()
        except Exception as e:
            self.send_error(404, str(e))
        finally:
            self.target.close()
             


    def _read_write(self, timeout=config.timeout, tick=3):
        timeout_max = timeout/tick
        socs = [self.target, self.connection]
        idling = 0
        while True:
            idling += 1
            (recv, _, error) = select.select(socs, [], socs, tick)
            if error:
                break
            if recv:
                for incoming in recv:
                    data = incoming.recv(config.buflen)
                    outgoing = self.target if incoming is self.connection else self.connection
                    if data:
                        outgoing.send(data)
                        idling = 0
            if idling == timeout_max:
                break


class ProxyServer(SocketServer.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_server():
    server_class = ProxyServer
    httpd = server_class((config.host, config.port), ProxyHandler)
    if not config.ssl_off:
        httpd.socket = ssl.wrap_socket(httpd.socket, 
                                   server_side=True,
                                   certfile=config.server_crt,
                                   keyfile=config.server_key,
                                   ca_certs=config.ca_crt,
                                   cert_reqs=ssl.CERT_REQUIRED)
#                                   ssl_version=ssl.PROTOCOL_TLSv1)
    print time.asctime(), "Server Starts - %s:%s" % (config.host, config.port)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print time.asctime(), "Server Stops" 


def main():
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", 
        help="Proxy server address",
        default=config.host)
    parser.add_argument("--port", 
        help="Proxy server port",
        type=int,
        default=config.port)
    parser.add_argument("--ssl_off", 
        help="Disable ssl connection",
        action="store_true",
        default=False)
    args = parser.parse_args()

    config.host = args.host 
    config.port = args.port
    config.ssl_off = args.ssl_off
    # start the proxy server
    start_server()


if __name__ == "__main__":
    main()
