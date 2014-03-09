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

import time
import util
from cloud.serialization import serialize, deserialize

MSG_TYPES = util.enum(unknown=0, getattr=1, value=2, method=3, call=4, exception=5)


class Message(object):
    """ Abstract class representing a message.
    A message contains a checksum (TODO) a timestamp and
    methods for serializing/deserializing it.
    
    """
    def __init__(self, checksum=None, timestamp=None):
        self.checksum = checksum
        self.timestamp = timestamp or time.time()
        
    def serialize(self):
        return serialize(self)

    @classmethod
    def deserialize(self, payload):
        return deserialize(payload)

    # TODO: __hash__
    

class REQMessage(Message):
    """ Request message that represents a remote evaluation on a Malacoda.
    """
    
    def __init__(self, fn_name, args=None, kwargs=None):
        self.fn_name = fn_name
        self.args = args
        self.kwargs = kwargs
        super(REQMessage, self).__init__()

    @property
    def is_getattr(self):
        return self.fn_name == 'getattr'

    @property
    def is_setattr(self):
        return self.fn_name == 'setattr'
    

class REPMessage(Message):
    """ Reply message representing the answer from a remote evaluation.
    """
    def __init__(self, typ=None, val=None):
        self.typ = typ
        self.val = val
        super(REPMessage, self).__init__()
        
    
