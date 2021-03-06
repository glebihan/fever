# FeverAccount.py
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

from EventsObject import EventsObject
from ThreadedTask import ThreadedTask
from db_structure import DB_STRUCTURE
import os
import sys
import logging
import fsutils
import json
import threading
import sqlite3
import gobject
import binascii
import time

from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.type import ttypes as EvernoteTypes

ELEMENTS_TYPES = ["tags", "notebooks", "resources", "notes"]

class FeverAccountDB(object):
    def __init__(self, db_file):
        self._db_file = db_file
        if not os.path.exists(os.path.split(self._db_file)[0]):
            fsutils.rec_mkdir(os.path.split(self._db_file)[0])
        self._db = sqlite3.Connection(self._db_file)
        self._db.text_factory = str
        
        self._main_thread = threading.current_thread()
        
        self._query_lock = threading.Lock()
        self._query_id = 0
        self._query_queue = {}
        self._query_results = {}
        
        gobject.timeout_add(10, self._check_query_queue)
        
        self._check_db_structure()
    
    def _check_query_queue(self):
        query_id = 0
        self._query_lock.acquire()
        if len(self._query_queue) > 0:
            query_id = self._query_queue.keys()[0]
            sql, params, condition = self._query_queue[query_id]
            del self._query_queue[query_id]
            condition.acquire()
            self._query_results[query_id] = self._do_query(sql, params)
            condition.notify()
            condition.release()
        self._query_lock.release()
        return True
    
    def _check_db_structure(self):
        for table_name in DB_STRUCTURE:
            self._query("CREATE TABLE IF NOT EXISTS `" + table_name + "` (" + ", ".join(["`" + field["field_name"] + "` " + field["type"] for field in DB_STRUCTURE[table_name]]) + ")")
    
    def _push_query(self, sql, params, condition):
        self._query_lock.acquire()
        self._query_id += 1
        self._query_queue[self._query_id] = (sql, params, condition)
        res = self._query_id
        self._query_lock.release()
        return res
    
    def _query_done(self, query_id):
        self._query_lock.acquire()
        res = (query_id in self._query_results)
        self._query_lock.release()
        return res
    
    def _do_query(self, sql, params = ()):
        cur = self._db.cursor()
        cur.execute(sql, params)
        res = cur.fetchall()
        cur.close()
        self._db.commit()
        return res
    
    def _query(self, sql, params = ()):
        if threading.current_thread() == self._main_thread:
            return self._do_query(sql, params)
        else:
            condition = threading.Condition()
            condition.acquire()
            query_id = self._push_query(sql, params, condition)
            while not self._query_done(query_id):
                condition.wait()
            condition.release()
            self._query_lock.acquire()
            res = self._query_results[query_id]
            self._query_lock.release()
            return res
    
    def get_global_data(self, key):
        data = self._query("SELECT `value` FROM global_data WHERE `key`=?", (key,))
        if len(data) == 1:
            res = data[0][0]
        else:
            res = None
        if key in ["lastSyncTime", "lastUpdateCount"]:
            if res == None:
                return 0
            else:
                return int(res)
        else:
            return res
    
    def set_global_data(self, key, value):
        self._query("DELETE FROM global_data WHERE `key`=?", (key,))
        self._query("INSERT INTO global_data (`key`, `value`) VALUES (?, ?)", (key, value))
    
    def _format_element(self, element_type, element):
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        res = {}
        for i in range(len(DB_STRUCTURE[element_type])):
            res[DB_STRUCTURE[element_type][i]["field_name"]] = element[i]
        return res
    
    def lookup_element_by_local_id(self, element_type, local_id):
        logging.debug("lookup_element_by_local_id %s %d" % (element_type, local_id))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        res = self._query("SELECT `" + "`, `".join([f["field_name"] for f in DB_STRUCTURE[element_type]]) + "` FROM " + element_type + " WHERE local_id=?", (local_id,))
        if len(res) == 1:
            return self._format_element(element_type, res[0])
    
    def lookup_element_by_guid(self, element_type, guid):
        logging.debug("lookup_element_by_guid %s %s" % (element_type, guid))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        res = self._query("SELECT `" + "`, `".join([f["field_name"] for f in DB_STRUCTURE[element_type]]) + "` FROM " + element_type + " WHERE guid=?", (guid,))
        if len(res) == 1:
            return self._format_element(element_type, res[0])
    
    def lookup_element_by_name(self, element_type, name):
        logging.debug("lookup_element_by_name %s %s" % (element_type, name))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        res = self._query("SELECT " + "`" + "`, `".join([f["field_name"] for f in DB_STRUCTURE[element_type]]) + "`" + " FROM " + element_type + " WHERE name=?", (name,))
        if len(res) == 1:
            return self._format_element(element_type, res[0])
    
    def create_element_from_server(self, element_type, element):
        logging.debug("create_element_from_server %s guid %s" % (element_type, element.guid))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
            
        field_list = [field for field in [f["field_name"] for f in DB_STRUCTURE[element_type] if not f["no_download"]] if field not in ["tagGuids"]] + ["dirty", "deleted"]
        values_list = [getattr(element, a) for a in [field for field in [f["field_name"] for f in DB_STRUCTURE[element_type] if not f["no_download"]] if field not in ["tagGuids"]]] + [0, 0]
        
        if element_type == "notes":
            field_list += ["tagGuids"]
            if element.tagGuids:
                values_list += [",".join(element.tagGuids)]
            else:
                values_list += [None]
        
        values_match_str = ", ".join(len(values_list) * ["?"])
        self._query("INSERT INTO " + element_type + " (`" + "`, `".join(field_list) + "`) VALUES (" + values_match_str + ")", tuple(values_list))
    
    def update_element_from_server(self, element_type, local_id, element):
        logging.debug("update_element_from_server %s guid %s" % (element_type, element.guid))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        field_list = [field for field in [f["field_name"] for f in DB_STRUCTURE[element_type] if not f["no_download"]] if field not in ["tagGuids", "content"]] + ["dirty", "deleted"]
        query_match_array = []
        values_list = [getattr(element, a) for a in [field for field in [f["field_name"] for f in DB_STRUCTURE[element_type] if not f["no_download"]] if field not in ["tagGuids", "content"]]] + [0, 0]
        
        if element_type == "notes":
            field_list += ["tagGuids"]
            if element.tagGuids:
                values_list += [",".join(element.tagGuids)]
            else:
                values_list += [None]
            
            if element.content != None:
                field_list += ["content"]
                values_list += [element.content]
        
        for field in field_list:
            query_match_array += ["%s=?" % field]
        query_match_str = ", ".join(query_match_array)
        
        self._query("UPDATE " + element_type + " SET " + query_match_str + " WHERE local_id=?", tuple(values_list) + (local_id,))
    
    def list_elements(self, element_type):
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
            
        elements = self._query("SELECT `" + "`, `".join([f["field_name"] for f in DB_STRUCTURE[element_type]]) + "` FROM " + element_type)
        res = []
        for element in elements:
            res.append(self._format_element(element_type, element))
        return res
    
    def delete_element(self, element_type, local_id):
        logging.debug("delete_element %s %d" % (element_type, local_id))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
            
        self._query("DELETE FROM " + element_type + " WHERE local_id=?", (local_id,))
    
    def rename_element(self, element_type, local_id, new_name):
        logging.debug("rename_element %s %d" % (element_type, local_id))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
            
        self._query("UPDATE " + element_type + " SET name=?, dirty=1 WHERE local_id=?", (new_name, local_id))
    
    def get_element(self, element_type, local_id):
        logging.debug("get_element %s %d" % (element_type, local_id))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        return self._format_element(element_type, self._query("SELECT `" + "`, `".join([f["field_name"] for f in DB_STRUCTURE[element_type]]) + "` FROM " + element_type + " WHERE local_id=?", (local_id,))[0])
    
    def get_element_by_hash(self, element_type, element_hash):
        logging.debug("get_element_by_hash %s %s" % (element_type, element_hash))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        return self._format_element(element_type, self._query("SELECT `" + "`, `".join([f["field_name"] for f in DB_STRUCTURE[element_type]]) + "` FROM " + element_type + " WHERE bodyHash=?", (element_hash,))[0])
    
    def update_element_field(self, element_type, field, local_id, value):
        logging.debug("update_element_field %s %s %d %s" % (element_type, field, local_id, value))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        if element_type == "notes":
            self._query("UPDATE " + element_type + " SET " + field + "=?, dirty=1, updated=? WHERE local_id=?", (value, 1000 * time.time(), local_id))
        else:
            self._query("UPDATE " + element_type + " SET " + field + "=?, dirty=1 WHERE local_id=?", (value, local_id))
    
    def create_new_note(self, notebook_local_id = None):
        if notebook_local_id == None:
            notebook_local_id = self._query("SELECT local_id FROM notebooks WHERE defaultNotebook=1")[0][0]
        self._query("INSERT INTO notes (title, dirty, content, notebook_local_id, created, updated) VALUES (?, 1, ?, ?, ?, ?)", (_("New note"), "<?xml version=\"1.0\" encoding=\"UTF-8\"?><!DOCTYPE en-note SYSTEM \"http://xml.evernote.com/pub/enml2.dtd\"><en-note></en-note>", notebook_local_id, 1000 * time.time(), 1000 * time.time()))
        return self._query("SELECT MAX(local_id) FROM notes")[0][0]
    
    def find_notebooks_by_stack(self, stack):
        notebooks = self._query("SELECT * FROM notebooks WHERE stack=?", (stack,))
        return [self._format_element("notebooks", n) for n in notebooks]
    
    def create_new_tag(self, tag_name):
        self._query("INSERT INTO tags (name, dirty) VALUES (?, 1)", (tag_name,))
        tag_local_id = self._query("SELECT MAX(local_id) FROM tags")[0][0]
        return self.lookup_element_by_local_id("tags", tag_local_id)
    
    def search_notes(self, **filters):
        query_str = "SELECT * FROM notes WHERE 1"
        query_params = ()
        if "notebook_filter" in filters and filters["notebook_filter"]:
            query_str += " AND notebook_local_id IN (" + ",".join([str(n) for n in filters["notebook_filter"]]) + ")"
        if "tag_filter" in filters and filters["tag_filter"]:
            query_str += " AND (tags_local_ids LIKE ? OR tags_local_ids LIKE ? OR tags_local_ids LIKE ? OR tags_local_ids = ?)"
            query_params += (str(filters["tag_filter"]) + ",%", "%," + str(filters["tag_filter"]) + ",%" , "%," + str(filters["tag_filter"]), str(filters["tag_filter"]))
        if "keyword" in filters and filters["keyword"]:
            words = filters["keyword"].rstrip().lstrip().split()
            for word in words:
                query_str += " AND (title LIKE ? OR content LIKE ?)"
                query_params += ("%" + word + "%", "%" + word + "%")
        if "created_after" in filters and filters["created_after"]:
            query_str += " AND created >= ?"
            query_params += (int(filters["created_after"]),)
        if "created_before" in filters and filters["created_before"]:
            query_str += " AND created <= ?"
            query_params += (int(filters["created_before"]),)
        if "modified_after" in filters and filters["modified_after"]:
            query_str += " AND updated >= ?"
            query_params += (int(filters["modified_after"]),)
        if "modified_before" in filters and filters["modified_before"]:
            query_str += " AND updated <= ?"
            query_params += (int(filters["modified_before"]),)
        
        sort_orders_map = {
            "date_created_desc": "created DESC",
            "date_created_asc": "created ASC",
            "date_modified_desc": "updated DESC",
            "date_modified_asc": "updated ASC",
            "title_asc": "title ASC",
            "title_desc": "title DESC"
        }
        if "sort_order" in filters and filters["sort_order"] in sort_orders_map:
            sort = sort_orders_map[filters["sort_order"]]
        else:
            sort = "created DESC"
        query_str += " ORDER BY " + sort
        
        elements = self._query(query_str, query_params)
        res = []
        for element in elements:
            res.append(self._format_element("notes", element))
        return res

class FeverAccount(EventsObject):
    def __init__(self, username):
        EventsObject.__init__(self)
        
        self._username = username
        self._account_data_file = os.path.join(os.getenv("HOME"), ".local", "share", "fever", "accounts", self._username + ".db")
        self._account_data_db = FeverAccountDB(self._account_data_file)
        
        self._sync_state_lock = threading.Lock()
        self._sync_state = ""
        
        self._sync_running_lock = threading.Lock()
        self._sync_running = False
        self._restart_sync = False
    
    def list_tags(self):
        return [tag for tag in self._account_data_db.list_elements("tags") if tag["deleted"] == False]
    
    def list_notebooks(self):
        return [notebook for notebook in self._account_data_db.list_elements("notebooks") if notebook["deleted"] == False]
    
    def find_notebooks_by_stack(self, stack):
        return self._account_data_db.find_notebooks_by_stack(stack)
    
    def find_tag_by_local_id(self, tag_local_id):
        return self._account_data_db.lookup_element_by_local_id("tags", tag_local_id)
    
    def find_tag_by_name(self, tag_name):
        return self._account_data_db.lookup_element_by_name("tags", tag_name)
    
    def create_new_tag(self, tag_name):
        return self._account_data_db.create_new_tag(tag_name)
    
    def list_notes(self):
        return [note for note in self._account_data_db.list_elements("notes") if note["deleted"] == False]
    
    def search_notes(self, **filters):
        return self._account_data_db.search_notes(**filters)
    
    def get_note(self, note_local_id):
        return self._account_data_db.get_element("notes", note_local_id)
    
    def update_note_contents(self, note_local_id, contents):
        self._account_data_db.update_element_field("notes", "content", note_local_id, contents)
    
    def update_note_title(self, note_local_id, title):
        self._account_data_db.update_element_field("notes", "title", note_local_id, title)
    
    def update_note_notebook(self, note_local_id, notebook_local_id):
        self._account_data_db.update_element_field("notes", "notebook_local_id", note_local_id, notebook_local_id)
        self._account_data_db.update_element_field("notes", "notebookGuid", note_local_id, "")
    
    def update_notebook_stack(self, notebook_local_id, stack):
        self._account_data_db.update_element_field("notebooks", "stack", notebook_local_id, stack)
    
    def add_note_tag(self, note_local_id, tag):
        note = self._account_data_db.lookup_element_by_local_id("notes", note_local_id)
        if note["tags_local_ids"]:
            tags_local_ids = [int(tag_local_id) for tag_local_id in note["tags_local_ids"].split(",")]
        else:
            tags_local_ids = []
        tags_local_ids += [tag["local_id"]]
        self._account_data_db.update_element_field("notes", "tags_local_ids", note_local_id, ",".join([str(t) for t in tags_local_ids]))
        self._account_data_db.update_element_field("notes", "tagGuids", note_local_id, "-1")
    
    def remove_note_tag(self, note_local_id, tag):
        note = self._account_data_db.lookup_element_by_local_id("notes", note_local_id)
        if note["tags_local_ids"]:
            tags_local_ids = [int(tag_local_id) for tag_local_id in note["tags_local_ids"].split(",")]
        else:
            tags_local_ids = []
        if tag["local_id"] in tags_local_ids:
            i = tags_local_ids.index(tag["local_id"])
            del tags_local_ids[i]
        self._account_data_db.update_element_field("notes", "tags_local_ids", note_local_id, ",".join([str(t) for t in tags_local_ids]))
        self._account_data_db.update_element_field("notes", "tagGuids", note_local_id, "-1")
    
    def create_new_note(self, notebook_local_id = None):
        return self._account_data_db.create_new_note(notebook_local_id)
    
    def get_resource_by_hash(self, resource_hash):
        return self._account_data_db.get_element_by_hash("resources", resource_hash)
    
    def destroy(self):
        self.disconnect_all()
    
    def authenticate(self):
        ThreadedTask(target = self._do_authenticate, callback = self._on_authentication_response).run()
    
    def _do_authenticate(self):
        logging.debug("_do_authenticate")
        
        if not self.token:
            return "need_token"
        
        try:
            client = EvernoteClient(token = self.token)
            userStore = client.get_user_store()
            user = userStore.getUser()
            if user.username != self._username:
                return "need_token"
            return "authentication_success"
        except:
            return "need_token"
    
    def _on_authentication_response(self, response):
        logging.debug("_on_authentication_response : %s" % response)
        self._trigger(response)
    
    def _get_token(self):
        return self._account_data_db.get_global_data("token")
    def _set_token(self, token):
        self._account_data_db.set_global_data("token", token)
    token = property(_get_token, _set_token)
    
    def _get_lastSyncTime(self):
        return self._account_data_db.get_global_data("lastSyncTime")
    def _set_lastSyncTime(self, lastSyncTime):
        self._account_data_db.set_global_data("lastSyncTime", lastSyncTime)
    lastSyncTime = property(_get_lastSyncTime, _set_lastSyncTime)
    
    def _get_lastUpdateCount(self):
        return self._account_data_db.get_global_data("lastUpdateCount")
    def _set_lastUpdateCount(self, lastUpdateCount):
        self._account_data_db.set_global_data("lastUpdateCount", lastUpdateCount)
    lastUpdateCount = property(_get_lastUpdateCount, _set_lastUpdateCount)
    
    def _get_sync_state(self):
        self._sync_state_lock.acquire()
        res = self._sync_state
        self._sync_state_lock.release()
        return res
    def _set_sync_state(self, sync_state):
        self._sync_state_lock.acquire()
        self._sync_state = sync_state
        self._sync_state_lock.release()
    sync_state = property(_get_sync_state, _set_sync_state)
    
    def _do_full_sync(self):
        logging.debug("_do_full_sync")
        try:
            self.sync_state = _("Starting...")
            chunk_filter = NoteStore.SyncChunkFilter(**{
                "includeNotes": True,
                "includeTags": True,
                "includeNotebooks": True,
                #~ "includeNoteResources": True,
                #~ "includeNoteAttributes": True,
                "includeResources": True,
                #~ "includeLinkedNotebooks": True,
                "includeExpunged": True
            })
            client = EvernoteClient(token = self.token)
            noteStore = client.get_note_store()
            
            self.sync_state = _("Retrieving data from server...")
            
            chunks_list = []
            chunk = noteStore.getFilteredSyncChunk(0, 100, chunk_filter)
            chunks_list.append(chunk)
            while chunk.chunkHighUSN < chunk.updateCount:
                chunk = noteStore.getFilteredSyncChunk(chunk.chunkHighUSN, 100, chunk_filter)
                chunks_list.append(chunk)
            
            elements = {"tags": [], "notebooks": [], "resources": [], "notes": []}
            for chunk in chunks_list:
                if chunk.tags:
                    elements["tags"] += chunk.tags
                if chunk.notebooks:
                    elements["notebooks"] += chunk.notebooks
                if chunk.resources:
                    elements["resources"] += chunk.resources
                if chunk.notes:
                    elements["notes"] += chunk.notes
            
            # Sync
            
            self.sync_state = _("Downloading...")
            
            elements_to_upload = {}
            elements_on_both_sides = {}
            created_elements = {}
            for element_type in ELEMENTS_TYPES:
                elements_to_upload[element_type] = []
                elements_on_both_sides[element_type] = []
                created_elements[element_type] = []
                for server_element in elements[element_type]:
                    client_element = self._account_data_db.lookup_element_by_guid(element_type, server_element.guid)
                    if client_element:
                        if server_element.updateSequenceNum == client_element["updateSequenceNum"] and not client_element["dirty"]:
                            # Nothing to do, element is in sync
                            pass
                        elif server_element.updateSequenceNum == client_element["updateSequenceNum"] and client_element["dirty"]:
                            if client_element["deleted"]:
                                if element_type == "tags":
                                    updateSequenceNum = noteStore.expungeTag(server_element.guid)
                                elif element_type == "notebooks":
                                    updateSequenceNum = noteStore.expungeNotebook(server_element.guid)
                                elif element_type == "notes":
                                    updateSequenceNum = noteStore.deleteNote(server_element.guid)
                            else:
                                elements_to_upload[element_type].append((server_element, client_element))
                        elif server_element.updateSequenceNum > client_element["updateSequenceNum"] and not client_element["dirty"]:
                            if element_type == "notes":
                                if server_element.contentHash != client_element["contentHash"]:
                                    server_element.content = noteStore.getNoteContent(server_element.guid)
                                server_element.notebook_local_id = self._account_data_db.lookup_element_by_guid("notebooks", server_element.notebookGuid)["local_id"]
                                tags_local_ids = []
                                if server_element.tagGuids:
                                    for tagGuid in server_element.tagGuids:
                                        tags_local_ids.append(str(self._account_data_db.lookup_element_by_guid("tags", tagGuid)["local_id"]))
                                server_element.tags_local_ids = ",".join(tags_local_ids)
                            elif element_type == "resources":
                                server_element.bodyHash = binascii.b2a_hex(server_element.data.bodyHash)
                                if server_element.data.bodyHash != binascii.b2a_hex(server_element.data.bodyHash):
                                    server_element.data = noteStore.getResourceData(server_element.guid)
                                else:
                                    server_element.data = client_element["data"]
                            self._account_data_db.update_element_from_server(element_type, client_element["local_id"], server_element)
                        elif server_element.updateSequenceNum > client_element["updateSequenceNum"] and client_element["dirty"]:
                            # Conflict
                            logging.warn("CONFLICT : server_element.updateSequenceNum > client_element[\"updateSequenceNum\"] and client_element[\"dirty\"]")
                        elements_on_both_sides[element_type].append(client_element["local_id"])
                    else:
                        if element_type in ["tags", "notebooks"]:
                            client_element = self._account_data_db.lookup_element_by_name(element_type, server_element.name)
                        else:
                            client_element = None
                        if client_element:
                            if client_element["dirty"]:
                                # Conflict
                                logging.warn("CONFLICT : client_element[\"dirty\"]")
                            else:
                                index = 2
                                new_name = "%s (%n)" % (client_element["name"], index)
                                while self._account_data_db.lookup_element_by_name(element_type, new_name):
                                    index += 1
                                    new_name = "%s (%n)" % (client_element["name"], index)
                                self._account_data_db.rename_element(element_type, client_element["local_id"], new_name)
                        else:
                            if element_type == "notes":
                                server_element.content = noteStore.getNoteContent(server_element.guid)
                                server_element.notebook_local_id = self._account_data_db.lookup_element_by_guid("notebooks", server_element.notebookGuid)["local_id"]
                                tags_local_ids = []
                                if server_element.tagGuids:
                                    for tagGuid in server_element.tagGuids:
                                        tags_local_ids.append(str(self._account_data_db.lookup_element_by_guid("tags", tagGuid)["local_id"]))
                                server_element.tags_local_ids = ",".join(tags_local_ids)
                            elif element_type == "resources":
                                server_element.bodyHash = binascii.b2a_hex(server_element.data.bodyHash)
                                server_element.data = noteStore.getResourceData(server_element.guid)
                            self._account_data_db.create_element_from_server(element_type, server_element)
                            created_elements[element_type].append(server_element.guid)
            
            #~ self.lastUpdateCount = chunk.updateCount
            #~ self.lastSyncTime = chunk.currentTime
            
            for element_type in ELEMENTS_TYPES:
                for client_element in self._account_data_db.list_elements(element_type):
                    if not client_element["local_id"] in elements_on_both_sides[element_type] and not client_element["guid"] in created_elements[element_type]:
                        if client_element["deleted"] == 1 or client_element["dirty"] == 0 or client_element["updateSequenceNum"]:
                            self._account_data_db.delete_element(element_type, client_element["local_id"])
                        else:
                            elements_to_upload[element_type].append((None, client_element))
            
            need_incremental_sync = False
            
            # Upload
            
            self.sync_state = _("Uploading...")
            
            for element_type in ELEMENTS_TYPES:
                for server_element, client_element in elements_to_upload[element_type]:
                    if not client_element["updateSequenceNum"]:
                        if element_type == "tags":
                            server_element = EvernoteTypes.Tag()
                        elif element_type == "notebooks":
                            server_element = EvernoteTypes.Notebook()
                        elif element_type == "notes":
                            server_element = EvernoteTypes.Note()
                    for field in [f["field_name"] for f in DB_STRUCTURE[element_type] if f["no_upload"] == False]:
                        if element_type == "notes" and client_element["notebookGuid"] == "":
                            # Note was moved to a different notebook
                            client_element["notebookGuid"] = self._account_data_db.lookup_element_by_local_id("notebooks", client_element["notebook_local_id"])["guid"]
                        if element_type == "notes" and client_element["tagGuids"] == "-1":
                            # Tags were changed
                            tagGuids = []
                            if client_element["tags_local_ids"]:
                                for tag_local_id in client_element["tags_local_ids"].split(","):
                                    tagGuids.append(self._account_data_db.lookup_element_by_local_id("tags", int(tag_local_id))["guid"])
                            client_element["tagGuids"] = ",".join(tagGuids)
                        if field in ["parentGuid", "stack"] and client_element[field] == "":
                            value = None
                        elif field in ["tagGuids"] and client_element[field] != "" and client_element[field] != None:
                            value = client_element[field].split(",")
                        else:
                            value = client_element[field]
                        setattr(server_element, field, value)
                    if client_element["updateSequenceNum"]:
                        if element_type == "tags":
                            updateSequenceNum = noteStore.updateTag(server_element)
                            new_server_element = noteStore.getTag(client_element["guid"])
                        elif element_type == "notebooks":
                            updateSequenceNum = noteStore.updateNotebook(server_element)
                            new_server_element = noteStore.getNotebook(client_element["guid"])
                        elif element_type == "notes":
                            server_element.notebookGuid
                            new_server_element = noteStore.updateNote(server_element)
                            updateSequenceNum = new_server_element.updateSequenceNum
                            new_server_element.notebook_local_id = client_element["notebook_local_id"]
                            tags_local_ids = []
                            if new_server_element.tagGuids:
                                for tagGuid in new_server_element.tagGuids:
                                    tags_local_ids.append(str(self._account_data_db.lookup_element_by_guid("tags", tagGuid)["local_id"]))
                            new_server_element.tags_local_ids = ",".join(tags_local_ids)
                        if updateSequenceNum == self.lastUpdateCount + 1:
                            self.lastUpdateCount = updateSequenceNum
                        else:
                            need_incremental_sync = True
                        self._account_data_db.update_element_from_server(element_type, client_element["local_id"], new_server_element)
                    else:
                        if element_type == "tags":
                            server_element = noteStore.createTag(server_element)
                        elif element_type == "notebooks":
                            server_element = noteStore.createNotebook(server_element)
                        elif element_type == "notes":
                            server_element = noteStore.createNote(server_element)
                            server_element.notebook_local_id = client_element["notebook_local_id"]
                            tags_local_ids = []
                            if server_element.tagGuids:
                                for tagGuid in server_element.tagGuids:
                                    tags_local_ids.append(str(self._account_data_db.lookup_element_by_guid("tags", tagGuid)["local_id"]))
                            server_element.tags_local_ids = ",".join(tags_local_ids)
                        self._account_data_db.update_element_from_server(element_type, client_element["local_id"], server_element)
            
            if need_incremental_sync:
                logging.debug("need_incremental_sync")
                self._do_sync()
            
            self.sync_state = ""
                    
        except:
            logging.error(sys.exc_info())
            self.sync_state = _("Error : " + str(sys.exc_info()))
    
    def _do_sync(self):
        logging.debug("_do_sync")
        if not self.lastSyncTime:
            self._do_full_sync()
        
        self._sync_running_lock.acquire()
        restart_sync = self._restart_sync
        self._restart_sync = False
        if not restart_sync:
            self._sync_running = False
        self._sync_running_lock.release()
        if restart_sync:
            self._do_sync()
    
    def sync(self):
        self._trigger("sync_start")
        self._sync_running_lock.acquire()
        if self._sync_running:
            self._restart_sync = True
            self._sync_running_lock.release()
            return
        self._sync_running = True
        self._sync_running_lock.release()
        ThreadedTask(target = self._do_sync, callback = self._on_sync_done).run()
    
    def _on_sync_done(self, response):
        logging.debug("_on_sync_done : %s" % response)
        self._trigger("sync_done")
