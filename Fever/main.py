# main.py
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
import logging
import json
import AboutDialog

from FeverAccount import FeverAccount
from HTMLNode import HTMLNode

from evernote.api.client import EvernoteClient
from evernote.edam.type import ttypes as Types

class Application(object):
    def __init__(self, cli_options):
        self.cli_options = cli_options
        self.cli_options.share_dir = os.path.abspath(self.cli_options.share_dir)
        
        self._account = None
        self._is_quitting = False
        
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(self.cli_options.share_dir, "fever", "ui", "ui.glade"))
        self._window = builder.get_object("main_window")
        
        self._webview = webkit.WebView()
        builder.get_object("webview_container").add(self._webview)
        self._webview.get_settings().set_property('enable-file-access-from-file-uris', 1)
        
        self._webview_load_finished = False
        self._webview_pending_commands = []
        self._webview.connect("load-finished", self._on_webview_load_finished)
        self._webview.connect("script-alert", self._on_webview_script_alert)
        
        self._webview.load_uri(urlparse.urljoin('file:', urllib.pathname2url(os.path.join(self.cli_options.share_dir, "fever", "ui", "main_window.html"))))
        
        self._statusbar = builder.get_object("statusbar")

        self._window.connect("delete_event", self._on_window_delete_event)
        builder.get_object("quit_action").connect("activate", self._on_quit_clicked)
        builder.get_object("sync_action").connect("activate", self._on_sync_clicked)
        builder.get_object("about_action").connect("activate", self._on_about_clicked)
        builder.get_object("new_note_action").connect("activate", self._on_new_note_clicked)
        
        self._window.maximize()
        
        self._about_dialog = AboutDialog.AboutDialog(self._window)
    
    def _on_webview_load_finished(self, webview, frame):
        if frame == webview.get_main_frame():
            while len(self._webview_pending_commands):
                command = self._webview_pending_commands[0]
                del self._webview_pending_commands[0]
                self._do_send_command(command)
            self._webview_load_finished = True
    
    def _do_send_command(self, command):
        self._webview.execute_script(command)
    
    def send_command(self, command):
        if self._webview_load_finished:
            self._do_send_command(command)
        else:
            self._webview_pending_commands.append(command)
    
    def _on_webview_script_alert(self, editor, frame, message):
        if ":" in message:
            i = message.index(":")
            command = message[:i]
            params = message[i+1:]
        else:
            command = message
            params = ""
        
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
        elif command == "edit_note":
            note_local_id = int(params)
            self.edit_note(note_local_id)
        elif command == "set_note_notebook":
            i = params.index(":")
            note_local_id = int(params[:i])
            notebook_local_id = int(params[i+1:])
            self._account.update_note_notebook(note_local_id, notebook_local_id)
        elif command == "update_notebook_stack":
            i = params.index(":")
            notebook_local_id = int(params[:i])
            stack = params[i+1:]
            self._account.update_notebook_stack(notebook_local_id, stack)
            self._refresh_display_notebooks()
            
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
        note_data = {
            "local_id": note_local_id,
            "notebook_local_id": note["notebook_local_id"],
            "title": self._htmlentities_encode(note['title']),
            "contents": str(document)
        }
        self.send_command("set_editing_note(%s)" % json.dumps(note_data))
    
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
    
    def _on_about_clicked(self, menuitem):
        self._about_dialog.run()
    
    def _on_new_note_clicked(self, menuitem):
        if self._account:
            note_local_id = self._account.create_new_note()
            self._refresh_display()
            self.edit_note(note_local_id)
    
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
        self._account.connect("sync_start", self._on_account_sync_start)
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
        self.send_command("clear_all()")
        
        if not self._account:
            return
            
        tags_list = self._account.list_tags()
        tags_list.sort(lambda a,b: cmp(a["name"].lower(), b["name"].lower()))
        client_tags_list = []
        for tag in tags_list:
            if tag["deleted"] == 0:
                client_tags_list.append({"label": tag["name"]})
        self.send_command("update_tags_list(%s)" % json.dumps(client_tags_list))
        
        self._refresh_display_notebooks()
        
        notes_list = []
        for note in self._account.list_notes():
            if note["deleted"] == 0:
                notes_list.append({
                    "local_id": note["local_id"],
                    "notebook_local_id": note["notebook_local_id"],
                    "title": self._htmlentities_encode(note['title'])
                })
        self.send_command("update_notes_list(%s)" % json.dumps(notes_list))
    
    def _refresh_display_notebooks(self):
        notebooks_list = self._account.list_notebooks()
        stacks = {}
        stackless_notebooks = []
        for notebook in notebooks_list:
            if notebook["deleted"] == 0:
                if notebook["stack"]:
                    if not notebook["stack"] in stacks:
                        stacks[notebook["stack"]] = []
                    stacks[notebook["stack"]].append(notebook)
                else:
                    stackless_notebooks.append(notebook)
        client_notebooks_list = []
        client_notebooks_list.append({"label": _("All notes"), "id": -1, "is_stack": False, "children": []})
        for stack in stacks:
            stacks[stack].sort(lambda a,b: cmp(a["name"].lower(), b["name"].lower()))
            client_notebooks_list[0]["children"].append({"id": stack, "label": stack, "is_stack": True, "children": [{"label": n["name"], "id": n["local_id"]} for n in stacks[stack]]})
        for notebook in stackless_notebooks:
            client_notebooks_list[0]["children"].append({"label": notebook["name"], "is_stack": False, "id": notebook["local_id"]})
        client_notebooks_list[0]["children"].sort(lambda a,b: cmp(a["label"].lower(), b["label"].lower()))
        self.send_command("update_notebooks_list(%s)" % json.dumps(client_notebooks_list))
        client_notebooks_list = [{'local_id': notebook['local_id'], 'label': notebook['name']} for notebook in notebooks_list if notebook["deleted"] == 0]
        client_notebooks_list.sort(lambda a,b: cmp(a["label"].lower(), b["label"].lower()))
        self.send_command("update_note_notebook_selector(%s)" % json.dumps(client_notebooks_list))
    
    def _on_account_authentication_success(self, account):
        account.sync()
    
    def _on_account_sync_start(self, account):
        if not self._is_quitting:
            gobject.timeout_add(100, self._watch_account_sync)
    
    def _watch_account_sync(self):
        if self._account:
            sync_state = self._account.sync_state
            if sync_state:
                self._statusbar.push(self._statusbar.get_context_id("sync"), _("Synchronizing : ") + sync_state)
                return True
        self._statusbar.push(self._statusbar.get_context_id("sync"), "")
        return False
    
    def run(self):
        gtk.gdk.threads_init()
        self._window.show_all()
        self._switch_account("gwlebihan")
        gtk.main()
