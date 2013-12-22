#! /usr/bin/python
# -*- coding=utf-8 -*-

import os
import sys
import threading
import webkit
import gtk, gobject

from FeverAccount import FeverAccount

from evernote.api.client import EvernoteClient
from evernote.edam.type import ttypes as Types

class NoteEditor(webkit.WebView):
    def __init__(self, application):
        webkit.WebView.__init__(self)

class FeverWindow(gtk.Window):
    def __init__(self, app):
        gtk.Window.__init__(self)
        self._app = app
        
        self.set_size_request(800, 600)
        self.maximize()

class Application(object):
    def __init__(self, cli_options):
        self._cli_options = cli_options
        
        self._account = None
        
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(cli_options.share_dir, "fever", "ui", "main.glade"))
        self._window = builder.get_object("main_window")
        self._window.connect("delete_event", self._on_window_delete_event)
        self._window.maximize()
        
        self._note_container = builder.get_object("note_container")
        self._note_editor = NoteEditor(self)
        self._note_container.add(self._note_editor)
        
        self._tags_liststore = builder.get_object("tags_liststore")
        self._notebooks_liststore = builder.get_object("notebooks_liststore")
        self._notes_treeview = builder.get_object("notes_treeview")
        self._notes_liststore = builder.get_object("notes_liststore")
        
        builder.get_object("sync_action").connect("activate", self._on_sync_clicked)
        builder.get_object("quit_action").connect("activate", self._on_quit_clicked)
        builder.get_object("notes_treeview").get_selection().connect("changed", self._notes_treeview_selection_changed)
    
    def edit_note(self, note_local_id):
        note = self._account.get_note(note_local_id)
        self._note_editor.load_html_string(note["content"], "https://www.evernote.com/")
    
    def _notes_treeview_selection_changed(self, selection):
        store, paths = selection.get_selected_rows()
        if len(paths) == 1:
            note_local_id = self._notes_liststore[paths[0]][0]
            self.edit_note(note_local_id)
    
    def _check_quit(self):
        gtk.main_quit()
        return False
    
    def _on_window_delete_event(self, window, event):
        return self._check_quit()
    
    def _on_sync_clicked(self, menuitem):
        if self._account:
            self._account.sync()
        
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
            self._account = None
        self._account = FeverAccount(username)
        self._account.connect("need_token", self._on_account_need_token)
        self._account.connect("authentication_success", self._on_account_authentication_success)
        self._account.connect("sync_done", self._on_account_sync_done)
        self._account.authenticate()
        self._refresh_display()
    
    def _on_account_sync_done(self, account):
        self._refresh_display()
        
    def _refresh_display(self):
        self._tags_liststore.clear()
        self._notebooks_liststore.clear()
        self._notes_liststore.clear()
        
        if not self._account:
            return
            
        tags_list = self._account.list_tags()
        tags_list.sort(lambda a,b: cmp(a["name"].lower(), b["name"].lower()))
        for tag in tags_list:
            self._tags_liststore.append([tag["local_id"], tag["name"]])
            
        notebooks_list = self._account.list_notebooks() 
        notebooks_list.sort(lambda a,b: cmp(a["name"].lower(), b["name"].lower()))
        for notebook in notebooks_list:
            self._notebooks_liststore.append([notebook["local_id"], notebook["name"]])
        
        for note in self._account.list_notes():
            self._notes_liststore.append([note["local_id"], note["title"]])
    
    def _on_account_authentication_success(self, account):
        account.sync()
    
    def run(self):
        gtk.gdk.threads_init()
        self._window.show_all()
        self._switch_account("gwlebihan")
        gtk.main()
