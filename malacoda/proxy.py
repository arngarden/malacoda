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
import cPickle as pickle
from zmq_socket import Socket
from message import REPMessage, REQMessage, MSG_TYPES


class Proxy(object):
    """ Proxy around a Malacoda-method
    """
    def __init__(self, name, address, attr=None):
        """
        Init Proxy with name and address of Malacoda-daemon.
        Optional attr denotes which attribute in Malacoda this is proxy for.
        address should be host:port to Malacoda, port is optional and can be left out if
        Malacoda is on localhost.
        """
        self.__dict__['name'] = name
        self.__dict__['address'] = address
        self.__dict__['attr'] = attr or 'self'
        self.__dict__['socket'] = None
        self._connect_to_malacoda()

    def _connect_to_malacoda(self):
        """ Connect to Malacodas message socket.
        """
        if not self.socket is None:
            self.socket.close()
        context = zmq.Context()
        self.__dict__['socket'] = Socket(context, zmq.REQ, default_timeout=None)
        self.socket.connect('tcp://%s' % self.address)

    def __getattr__(self, attr):
        """ Send getattr-command to Malacoda and return result of evaluation.

        Args:
         - attr (basestring): Name of attribute to access.
        Returns:
         - Result of getattr-evaluation on the remote Malacoda, can be a proxy around
           a method or a value.
        Raises:
         - Reraises any exception from the remote evalution.
         
        """
        request = REQMessage('getattr', args=[self.attr, attr])
        return self._remote_eval(request, attr)

    def __setattr__(self, attr, value):
        """ Send setattr-command to Malacoda.

        Args:
         - attr (basestring): Name of attribute to set.
         - value: Value.
        Raises:
         - Reraises any exception from the remote evalution.
         
        """
        request = REQMessage('setattr', args=[self.attr, attr, value])
        return self._remote_eval(request)
    
    def __call__(self, *args, **kwargs):
        """ Execute call on malacoda and return result.

        """
        timeout = None
        if 'timeout' in kwargs:
            timeout = kwargs.pop('timeout')
        request = REQMessage(self.attr, args, kwargs)
        return self._remote_eval(request, timeout=timeout)

    def _remote_eval(self, request, attr=None, timeout=None):
        """ Evaluate request remotely.
        Depending on the reply the following can happen:
         - An exception from the remote eval is reraised
         - A value is returned, i.e a constant attribute or result of evaluation
         - A MalacodaProxy around a method is returned

        Args:
         - request (REQMessage): Message-object containing the request.
         - attr (basestring): An attribute we are evaluating.
         - timeout (int): Socket timeout in seconds (default no timeout)
        Returns:
         - Proxy around method or a value.
        Raises:
         - Reraises any exception from the remote evaluation
         
        """
        reply = self.socket.request_reply(request, REPMessage, timeout=timeout)
        if reply.typ == MSG_TYPES.exception:
            raise reply.val
        if attr and not reply.typ == MSG_TYPES.value:
            return Proxy(self.name, self.address, attr=attr)
        else:
            return reply.val

    def __str__(self):
        return 'Proxy for %s:%s' % (self.name, self.address)
