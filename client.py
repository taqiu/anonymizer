#! /usr/bin/python

#######################################
#
#  Python Proxy client
# 
#  Author: Tanghong Qiu
#  E-mail: taqiu@gmail.com
#    Date: Apr 6, 2014
#
#######################################

__version__ = '1.0'

import SocketServer
import argparse
import time
import socket
import select
import BaseHTTPServer
import ssl


class Config:
    def __init__(self):
        self.timeout = 180
        self.buflen  = 8192
        self.ssl_off = False
        self.white_list = {'127.0.0.1'}
        self.remote_host = '129.79.247.5'
        self.remote_port = 50000
        self.local_host = 'localhost'
        self.local_port = 8080
        self.client_key = 'auth/client.key'
        self.client_crt = 'auth/client.crt'
        self.ca_crt     = 'auth/server.crt'
        
config = Config()


class LocalProxyHandler(SocketServer.BaseRequestHandler):
    
    def setup(self):
        self.remote_host = config.remote_host
        self.remote_port = config.remote_port
        self.remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


    def handle(self):
        # valid client ip address
        (ip, port) =  self.client_address
        if  ip not in config.white_list:
            self._send_error("Your ip [%s] are not allowed to connect this proxy." % ip)
            return
        
        try:
            # connect remote proxy server
            self._connect_remote()
            # simply forward data
            self.local = self.request
            self._read_write()
        except Exception as e:
            info = "Please check your configuration or try later.</br>"
            info += str(e)
            self._send_error("<html><body><h1>Remote Proxy Error</h1>%s</body></html>" % info)


    def finish(self):
        self.remote.close()
        self.request.close()

    
    def _send_error(self, info):
        header = "HTTP/1.1 500 Remote Proxy Error\r\n"
        header += "Cache-Control: no-cache\r\n"
        header += "Connection: close\r\n"
        header += "Content-Type: text/html\r\n\r\n"
        try:
            self.request.send(header + info + '\r\n')
        except:
            pass
        


    def _connect_remote(self):
        # connect remote server with ssl
        if not config.ssl_off:
            self.remote = ssl.wrap_socket(self.remote,
                                          certfile=config.client_crt,
                                          keyfile=config.client_key,
                                          cert_reqs=ssl.CERT_REQUIRED,
                                          ca_certs=config.ca_crt )
        self.remote.connect((self.remote_host, self.remote_port))


    def _read_write(self, timeout=config.timeout, tick=3):
        timeout_max = timeout/tick
        socs = [self.remote, self.local]
        idling = 0
        while True:
            idling += 1
            (recv, _, error) = select.select(socs, [], socs, tick)
            if error:
                break
            if recv:
                for incoming in recv:
                    data = incoming.recv(config.buflen)
                    if incoming is self.local:
                        outgoing = self.remote
                    else:
                        outgoing = self.local
                    if data:
                        outgoing.send(data)
                        idling = 0
            if idling == timeout_max:
                break


class LocalProxyServer(SocketServer.ThreadingTCPServer):
    """Local Proxy Server"""
    allow_reuse_address = True # Prevent 'cannot bind to address' errors on restart
    daemon_threads = True 


def start_server():
    # Create the server
    server = LocalProxyServer((config.local_host, config.local_port), LocalProxyHandler)
    print time.asctime(), "Server Starts - %s:%s" % (config.local_host, config.local_port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.shutdown()
    print time.asctime(), "Server Stops" 


def main():
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--remote_host", 
        help="Remote proxy server address",
        default=config.remote_host)
    parser.add_argument("--remote_port", 
        help="Remote proxy server port",
        type=int,
        default=config.remote_port)
    parser.add_argument("--local_host", 
        help="Local proxy server address",
        default=config.local_host)
    parser.add_argument("--local_port", 
        help="Local proxy server port",
        type=int,
        default=config.local_port)
    parser.add_argument("--ssl_off", 
        help="Disable ssl connection",
        action="store_true",
        default=False)
    args = parser.parse_args()

    config.remote_host = args.remote_host 
    config.remote_port = args.remote_port
    config.local_host  = args.local_host 
    config.local_port  = args.local_port 
    config.ssl_off = args.ssl_off
    # start the local proxy server
    start_server()


if __name__ == "__main__":
    main()
