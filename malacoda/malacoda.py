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

import os
import sys
import signal
import daemon
import time
import zmq
import threading
import cPickle as pickle
import socket
import setproctitle
from subprocess import Popen, PIPE
from datetime import datetime, timedelta
from zmq_socket import Socket
from paramiko import SSHClient
import proxy
import signal
from message import REPMessage, REQMessage, MSG_TYPES
import pst_storage


class MalacodaException(Exception):
    pass


class Malacoda(daemon.DaemonContext):
    """ Malacoda is a daemon that can communicate with other Malacodas, keep persistant
    storage and more.
    """
    DEFAULT_PST_CONFIG = {'class_name': 'PstFileStorage', 'frequency': timedelta(minutes=1)}
    
    def __init__(self, name=None, bind_address=None, port=None, daemonize=True,
                 pst_config=None, **kwargs):
        """ Init Malacoda.
        Name of Malacoda can be overridden, else class name will be used.
        It is possible to override the address and port used for communicating with the Malacoda.
        If not, a port in MsgListenerThread.PORT_RANGE will be used and it will bind to
        MsgListenerThread.BIND_ADDRESS.
        If daemonize is set to False it will not go into the daemon context, this can be
        useful for testing or when the program need to run in the foreground.
        A persistant storer can be used if pst_config is set, this allows for saving variables
        starting with 'pst' to file or other persistant storage. The persistant storage is
        loaded when Malacoda is initialized. To enable persistant storage, pst_config should be a
        dict with a key 'class_name' that is the name of a PstStorage-class, (in pst_storage.py),
        any other keys in the dict are sent into the constructor of the PstStorage-class.
        Any remaining keyword arguments are forwarded into daemon.DaemonContext.
        
        Args:
         - name (basestring): Name of Malacoda.
         - bind_address (basestring): Bind communication to this address.
         - port (int): Bind communication to this port.
         - daemonize (bool): Whether to go into daemon context or not.
         - pst_config (dict): Persistant storage class name and arguments to that class.
                              For example {'class_name': 'PstFileStorage',
                                           'frequency': timedelta(minutes=5)}
         - kwargs: Optional keyword arguments that are sent to daemon.DaemonContext
         
        """
        if daemonize:
            super(Malacoda, self).__init__(**kwargs)
        self.running = False
        self.finished = False
        self.name = name or self.__class__.__name__
        setproctitle.setproctitle(self.name)
        self.daemonize = daemonize
        pst_config = pst_config or self.DEFAULT_PST_CONFIG
        try:
            class_name = pst_config.pop('class_name')
        except KeyError:
            raise MalacodaException('pst_config must have class_name')
        try:
            self.persistant_storage = getattr(pst_storage, class_name)(**pst_config)
        except AttributeError:
            raise MalacodaException('Unknown persistant storage class')
        self._load_pst()
        self.run(bind_address, port)

    def run(self, bind_address, port=None):
        """ Start message listener thread and main loop of daemon.

        Args:
         - bind_address (basestring): Optional host to bind message listener to.
         - port (int): Optional port to bind message listener.
         
        """
        self.running = True
        if self.daemonize:
            self.open()

        MsgListenerThread(self, bind_address=bind_address, port=port).start()
        threading.Thread(target=self._pst_handler).start()
        self._run()

    def _run(self):
        """ Main loop that needs to be overriden.
        This should be of form:
          while self.running:
            do work
            
        """
        raise NotImplemented

    def _load_pst(self):
        """ Load variables from persistant storage.
        
        """
        psts = self.persistant_storage.load()
        if psts:
            for name, value in psts:
                setattr(self, name, value)

    def _pst_handler(self):
        """ Loop that calls self.persistant_storage.save
        """
        self.last_pst = datetime.utcnow()
        while self.running:
            if self.last_pst + self.persistant_storage.frequency <= datetime.utcnow():
                psts = [(name, (getattr(self, name))) for name in dir(self)
                        if name.startswith('pst')]
                if psts:
                    self.persistant_storage.save(psts)
                self.last_pst = datetime.utcnow()
            time.sleep(5)

    def evaluate(self, msg):
        """ Evaluate message and return result.

        Args:
         - msg (REQMessage): The message.
        Returns:
         - (REPMessage) The reply message.
         
        """
        if msg.is_getattr:
            return self._getattr(msg)
        elif msg.is_setattr:
            return self._setattr(msg)
        else:
            return self._call(msg)

    def _getattr(self, msg):
        """ Perform getattr-call on this class and return reply message with result of call.
        The reply message can contain any of the following:
         - An exception if the getattr-call failed.
         - Name of a callable method in this class.
         - A value from the getattr-call.

        Args:
         - msg (REQMessage): The message.
        Returns:
         - (REPMessage): The reply message.
         
        """
        try:
            val = getattr(eval(msg.args[0]), msg.args[1])
        except AttributeError as e:
            rep_msg = REPMessage(typ=MSG_TYPES.exception, val=e)
        else:
            if callable(val):
                rep_msg = REPMessage(typ=MSG_TYPES.method, val=val.__name__)
            else:
                rep_msg = REPMessage(typ=MSG_TYPES.value, val=val)
        return rep_msg

    def _setattr(self, msg):
        """ Perform a setattr on this class.
        The reply message is either None or an exception.

        Args:
         - msg (REQMessage): The message.
        Returns:
         - (REPMessage): Reply message.

        """
        try:
            setattr(eval(msg.args[0]), msg.args[1], msg.args[2])
        except Exception as e:
            rep_msg = REPMessage(typ=MSG_TYPES.exception, val=e)
        else:
            rep_msg = REPMessage(typ=MSG_TYPES.value, val=None)
        return rep_msg

    def _call(self, msg):
        """ Perform call on this class and return reply message with result of call.
        The reply message can contain any of the following:
         - An exception if the call failed.
         - The result of the call

        Args:
         - msg (REQMessage): The message.
        Returns:
         - (REPMessage): The reply message.
         
        """
        try:
            val = getattr(self, msg.fn_name)(*msg.args, **msg.kwargs)
        except Exception as e:
            rep_msg = REPMessage(typ=MSG_TYPES.exception, val=e)
        else:
            rep_msg = REPMessage(typ=MSG_TYPES.call, val=val)
        return rep_msg

    def stop(self):
        """ Stop the daemon.
        """
        self.running = False
        if self.daemonize:
            self.close()


class MsgListenerThread(threading.Thread):
    """ MsgListenerThread listens to incoming request messages, evalutes these
    and returns reply message.
    
    """
    BIND_ADDRESS = '0.0.0.0'
    PORT_RANGE = (51000, 51100)

    def __init__(self, malacoda_obj, bind_address=None, port=None):
        """ Init MsgListenerThread.

        Args:
         - malacoda_obj (Malacoda): The Malacoda-object that evaluates the requests.
         - bind_address (basestring): Address to bind listener to, host:port or just host.
         - port (int): Optional port to bind listener to.
         
        """
        threading.Thread.__init__(self)
        self.malacoda_obj = malacoda_obj
        self.bind_address = bind_address or self.BIND_ADDRESS
        self.port = port
        self.socket = None
        self.ongoing_calls = {}
        self._connect()
        
    def _connect(self):
        """ Connect to listening socket.

        Raises:
         - MalacodaException - If no free ports can be find to connect to.
         
        """
        if not self.socket is None:
            self.socket.close()
        context = zmq.Context()
        self.socket = Socket(context, zmq.REP, default_timeout=None)
        if self.port:
            self.socket.bind('tcp://%s:%s' % (self.bind_address, self.port))
        else:
            for port in xrange(self.PORT_RANGE[0], self.PORT_RANGE[1]):
                try:
                    self.socket.bind('tcp://%s:%s' % (self.bind_address, port))
                    return
                except socket.timeout:
                    pass
            raise MalacodaException('Could not find free port to connect to')

    def run(self):
        """ Listen to incoming messages, handle these and return response.

        """
        while self.malacoda_obj.running:
            payload = self.socket.recv(timeout=None)
            msg = REQMessage.deserialize(payload) 
            rep_msg = self.malacoda_obj.evaluate(msg)
            self.socket.send(rep_msg.serialize() or '', timeout=None)

    
def get(name, **ssh_args):
    """ Return proxy for daemon with given name.
    name should be on format <name>:<host> where host is optional if daemon is on localhost.
    Raise exception or return None? if no daemon with name is found/running.
    TODO: Test proxy connection, if not working return None
    
    """
    port = _get_port(name, **ssh_args)
    if not port:
        raise MalacodaException('Could not find port for process with name: %s' % name)
    if ':' in name:
        name, host = name.split(':')
    else:
        host = 'localhost'
    address = '%s:%s' % (host, port)
    zp = proxy.Proxy(name, address)
    return zp


# TODO: this is perhaps not the best way..
FIND_PID_CMD = "ps xm | awk '/%s/ {print $1}'"
FIND_PORT_CMD = "lsof -a -p%s | awk '/LISTEN/ {print $9}'"

def _get_port(name, **ssh_args):
    """ Get port that pid is listening to.
    Would have preferred to use psutil for this, but not sure if I could make it
    work over SSH..
    
    """
    if ':' in name:
        name, host = name.split(':')
    else:
        host = None
    if not host:
        # look for Malacoda on local host
        pid = Popen(FIND_PID_CMD % name, stdout=PIPE, shell=True).communicate()[0].strip()
        out = Popen(FIND_PORT_CMD % pid,  stdout=PIPE,
                    shell=True).communicate()[0]
    else:
        # use SSH to access host and look up port
        client = SSHClient()
        client.load_system_host_keys()
        client.connect(host, **ssh_args)
        _, stdout, _ = client.exec_command(FIND_PID_CMD % name)
        pid = stdout.read().strip()
        if '\n' in pid:
            pid = pid.split('\n')[0]
        _, stdout, _ = client.exec_command(FIND_PORT_CMD % pid)
        out = stdout.read()
    port = out.split(':')[1].strip()
    return port

def stop(name):
    """ Stop daemon with given name
    """
    get(name).stop()



