# -*- coding: utf-8 -*-

"""
Copyright 2014 Gustav Arngården 

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import zmq
import socket
from functools import wraps
from message import REPMessage, REQMessage


class Socket(object):
    """ Proxy for ZMQ socket that adds timeout.
    """

    def __init__(self, ctx, stype, default_timeout=None):
        self.socket = zmq.Socket(ctx, stype)
        self.default_timeout = default_timeout

    def _timeout_wrapper(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            timeout = kwargs.pop('timeout', self.default_timeout)
            if timeout is not None:
                timeout = int(timeout * 1000)
                poller = zmq.Poller()
                poller.register(self.socket)
                if not poller.poll(timeout):
                    raise socket.timeout
            return f(self, *args, **kwargs)
        return wrapper

    def request_reply(self, msg, msg_class, timeout=None):
        self.send(msg.serialize(), timeout=timeout)
        payload = self.recv(timeout=timeout)
        return msg_class.deserialize(payload)
                    
    @_timeout_wrapper
    def send(self, *args, **kwargs):
        return self.socket.send(*args, **kwargs)

    @_timeout_wrapper
    def recv(self, *args, **kwargs):
        return self.socket.recv(*args, **kwargs)

    def __getattr__(self, attr):
        return getattr(self.socket, attr)
