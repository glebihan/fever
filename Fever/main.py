#! /usr/bin/python
# -*- coding=utf-8 -*-

import os
import sys
import threading
from gi.repository import Gtk, Gdk, GObject

from FeverAccount import FeverAccount

from evernote.api.client import EvernoteClient
from evernote.edam.type import ttypes as Types

class FeverWindow(Gtk.Window):
    def __init__(self, app):
        Gtk.Window.__init__(self)
        self._app = app
        
        self.set_size_request(800, 600)
        self.maximize()

class Application(object):
    def __init__(self, cli_options):
        self._cli_options = cli_options
        
        self._account = None
        
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(cli_options.share_dir, "fever", "ui", "main.glade"))
        self._window = builder.get_object("main_window")
        self._window.connect("delete_event", self._on_window_delete_event)
        self._window.maximize()
        
        builder.get_object("quit_action").connect("activate", self._on_quit_clicked)
    
    def _check_quit(self):
        Gtk.main_quit()
        return False
    
    def _on_window_delete_event(self, window, event):
        return self._check_quit()
    
    def _on_quit_clicked(self, menuitem):
        self._check_quit()
    
    def _on_account_need_token(self, account):
        f = open(os.path.join(os.path.split(sys.argv[0])[0], "evernote_dev_token"))
        account.token = f.read().splitlines()[0]
        f.close()
        account.authenticate()
    
    def _switch_account(self, username):
        if self._account:
            self._account.destroy()
        self._account = FeverAccount(username)
        self._account.connect("need_token", self._on_account_need_token)
        self._account.connect("authentication_success", self._on_account_authentication_success)
        self._account.connect("sync_done", lambda a: self._check_quit())
        self._account.authenticate()
    
    def _on_account_authentication_success(self, account):
        account.sync()
    
    def run(self):
        Gdk.threads_init()
        #~ self._window.show_all()
        self._switch_account("gwlebihan")
        Gtk.main()
        #~ dev_token = "S=s1:U=8d7fa:E=14a6bbc4604:C=143140b1a06:P=1cd:A=en-devtoken:V=2:H=bc2eeee6b3b3c781b06abc8d25ee2a69"
        #~ client = EvernoteClient(token=dev_token)
        #~ userStore = client.get_user_store()
        #~ user = userStore.getUser()
        #~ print user.username
        #~ 
        #~ noteStore = client.get_note_store()
        #~ notebooks = noteStore.listNotebooks()
        #~ for n in notebooks:
            #~ print n.name
        #~ 
        #~ noteStore = client.get_note_store()
        #~ note = Types.Note()
        #~ note.title = "I'm a test note!"
        #~ note.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        #~ note.content += '<en-note>Hello, world!</en-note>'
        #~ note = noteStore.createNote(note)
