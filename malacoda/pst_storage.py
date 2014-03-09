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
from datetime import timedelta
import cPickle as pickle


class PstStorageException(Exception):
    pass


class PstStorage(object):
    """ Base class for persistant storage.
    """
    
    def __init__(self, frequency=None):
        """ Init PstStorage.

        Args:
         - frequency (timedelta): Call method save with this frequency.
                                  For example timedelta(minutes=1) will save persistant
                                  variables once a minute.
        """
        self.frequency = frequency

    def save(self, psts):
        """ Persist given variables.

        Args:
         - psts (list): Variables to be persisted, [(variable name, value)]
        Raises:
         PstStorageException: If persisting failed.
         
        """
        raise NotImplemented

    def load(self):
        """ Load saved variables and return them.

        Returns:
         (list): Saved variables on form [(variable name, value)]
         
        """
        raise NotImplemented


class PstFileStorage(PstStorage):
    """ Saves variables to pickle file.
    """
    DEFAULT_PST_FILE = '/tmp/pst.p'
    
    def __init__(self, file_path=None, frequency=None):
        """ Init PstFileStorage.

        Args:
         - file_path (basestring): Complete path to file for saving variables.
         - frequency (timedelta): Call method save with this frequency.
                                  For example timedelta(minutes=1) will save persistant
                                  variables once a minute.
        """
        self.file_path = file_path or self.DEFAULT_PST_FILE
        frequency = frequency or timedelta(minutes=1)
        super(PstFileStorage, self).__init__(frequency)
        
    def save(self, psts):
        """ Save variables to pickle file.
        """
        try:
            pickle.dump(psts, open(self.file_path, 'wb'))
        except Exception as e:
            raise PstStorageException('Could not save variable to file: %s' % e)
            
    def load(self):
        """ Load variables from pickle file.
        """
        if not os.path.isfile(self.file_path):
            return []
        try:
            psts = pickle.load(open(self.file_path, 'rb'))
            return psts
        except Exception as e:
            raise PstStorageException('Could not load variables from file: %s' % e)
        
