# ThreadedTask.py
# -*- Mode: Python; indent-tabs-mode: nil; tab-width: 4; coding: utf-8 -*-
#
# Copyright © 2013-2014 Gwendal Le Bihan
# 
# This file is part of Fever.
# 
# Fever is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Fever is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Fever.  If not, see <http://www.gnu.org/licenses/>.

import threading
import gobject

class ThreadedTask(object):
    def __init__(self, group = None, target = None, name = None, args = (), kwargs = {}, callback = None):
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._callback = callback
        self._thread = threading.Thread(group, self._do_run, name)
        self._thread_done = threading.Event()
        gobject.timeout_add(100, self._check_done)
    
    def _check_done(self):
        if self._thread_done.is_set():
            if self._callback:
                self._callback(self._result)
            return False
        else:
            return True
    
    def _do_run(self):
        self._result = self._target(*self._args, **self._kwargs)
        self._thread_done.set()
    
    def run(self):
        self._thread.start()
