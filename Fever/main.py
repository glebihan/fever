#! /usr/bin/python
# -*- coding=utf-8 -*-

import os
import sys
import threading
import webkit
import gtk
import gobject
import libxml2
import binascii
import urllib
import urlparse
import htmlentitydefs

from FeverAccount import FeverAccount
from HTMLNode import HTMLNode

from evernote.api.client import EvernoteClient
from evernote.edam.type import ttypes as Types

class NoteEditor(webkit.WebView):
    def __init__(self, application):
        webkit.WebView.__init__(self)
        settings = self.get_settings()
        settings.set_property('enable-file-access-from-file-uris', 1)

class FeverWindow(gtk.Window):
    def __init__(self, app):
        gtk.Window.__init__(self)
        self._app = app
        
        self.set_size_request(800, 600)
        self.maximize()

class Application(object):
    def __init__(self, cli_options):
        self._cli_options = cli_options
        self._cli_options.share_dir = os.path.abspath(self._cli_options.share_dir)
        
        self._account = None
        self._is_quitting = False
        
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(cli_options.share_dir, "fever", "ui", "main.glade"))
        self._window = builder.get_object("main_window")
        self._window.connect("delete_event", self._on_window_delete_event)
        self._window.maximize()
        
        self._note_container = builder.get_object("note_container")
        self._note_editor = NoteEditor(self)
        self._note_container.add(self._note_editor)
        self._note_editor.connect("script-alert", self._on_note_editor_message)
        
        self._tags_liststore = builder.get_object("tags_liststore")
        self._notebooks_liststore = builder.get_object("notebooks_liststore")
        self._notes_treeview = builder.get_object("notes_treeview")
        self._notes_liststore = builder.get_object("notes_liststore")
        
        builder.get_object("sync_action").connect("activate", self._on_sync_clicked)
        builder.get_object("quit_action").connect("activate", self._on_quit_clicked)
        builder.get_object("notes_treeview").get_selection().connect("changed", self._notes_treeview_selection_changed)
    
    def _on_note_editor_message(self, editor, frame, message):
        i = message.index(":")
        command = message[:i]
        params = message[i+1:]
        
        if command == "set_note_contents":
            i = params.index(":")
            note_local_id = int(params[:i])
            contents = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\"><en-note>" + params[i+1:] + "</en-note>"
            self._account.update_note_contents(note_local_id, contents)
        elif command == "set_note_title":
            i = params.index(":")
            note_local_id = int(params[:i])
            title = params[i+1:]
            self._account.update_note_title(note_local_id, title)
            
        return True
    
    def edit_note(self, note_local_id):
        note = self._account.get_note(note_local_id)
        tree = libxml2.htmlParseDoc(note["content"], "utf-8")
        document = HTMLNode(tree.getRootElement())
        for img in document.find("en-media"):
            resource = self._account.get_resource_by_hash(img.prop("hash"))
            new_img = libxml2.newNode("img")
            new_img.newProp("src", "data:%s;base64,%s" % (resource['mime'], binascii.b2a_base64(resource['data'])))
            new_img.newProp("hash", img.prop("hash"))
            img.replaceNode(new_img)
        contents = """
        <script type='text/javascript' src='%s'></script>
        <script type="text/javascript">
        tinymce.init({
            selector: "#tinymce",
            setup: function(editor){
                editor.on('change', function(e){
                    alert('set_note_contents:%d:' + editor.getContent());
                });
            },
            toolbar: false,
            menubar: false,
            statusbar: false
         });
        </script>
        <input type='text' id='title' value='%s' style='width: 100%%; border: none; outline: none; padding: 0; line-height: 15px; font-size: 15px; color: #7b7c7e; font-family: caecilia, serif; height: 32px;'/>
        <div id='tinymce'>%s</div>
        <script type="text/javascript">
        document.getElementById('title').onchange = function(event){
            alert('set_note_title:%d:' + document.getElementById('title').value);
        }
        </script>
        """ % (urlparse.urljoin('file:', urllib.pathname2url(os.path.join(self._cli_options.share_dir, "fever", "tinymce", "js", "tinymce", "tinymce.min.js"))), note['local_id'], self._htmlentities_encode(note['title']), str(document), note['local_id'])
        self._note_editor.load_html_string(contents, "file:///")
    
    def _htmlentities_encode(self, string):
        res = ""
        for i in unicode(string):
            if ord(i) in htmlentitydefs.codepoint2name:
                res += "&" + htmlentitydefs.codepoint2name[ord(i)] + ";"
            elif i == "'":
                res += "&#039;"
            else:
                res += i
        return res
    
    def _notes_treeview_selection_changed(self, selection):
        store, paths = selection.get_selected_rows()
        if len(paths) == 1:
            note_local_id = self._notes_liststore[paths[0]][0]
            self.edit_note(note_local_id)
    
    def _check_quit(self):
        self._window.hide()
        self._is_quitting = True
        if self._account:
            self._account.sync()
        else:
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
        if self._is_quitting:
            gtk.main_quit()
        else:
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
