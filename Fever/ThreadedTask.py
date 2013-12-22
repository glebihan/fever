#! /usr/bin/python
# -*- coding=utf-8 -*-

import threading
from gi.repository import GObject

class ThreadedTask(object):
    def __init__(self, group = None, target = None, name = None, args = (), kwargs = {}, callback = None):
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._callback = callback
        self._thread = threading.Thread(group, self._do_run, name)
        self._thread_done = threading.Event()
        GObject.timeout_add(100, self._check_done)
    
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
