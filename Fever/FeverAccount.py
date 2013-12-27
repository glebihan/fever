#! /usr/bin/python
# -*- coding=utf-8 -*-

from EventsObject import EventsObject
from ThreadedTask import ThreadedTask
import os
import sys
import logging
import fsutils
import json
import threading
import sqlite3
import gobject
import binascii

from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.type import ttypes as EvernoteTypes

ELEMENTS_TYPES = ["tags", "notebooks", "resources", "notes"]
ELEMENTS_FIELDS = {
    "tags": ["local_id", "guid", "name", "parentGuid", "updateSequenceNum", "dirty", "deleted"],
    "notebooks": ["local_id", "guid", "name", "updateSequenceNum", "defaultNotebook", "dirty", "deleted"],
    "resources": ["local_id", "guid", "noteGuid", "data", "bodyHash", "mime", "width", "height", "updateSequenceNum", "dirty", "deleted"],
    "notes": ["local_id", "guid", "title", "content", "contentHash", "contentLength", "active", "updateSequenceNum", "notebookGuid", "tagGuids", "dirty", "deleted"]
}
ELEMENTS_UPLOAD_FIELDS = {
    "tags": ["name"],
    "notebooks": ["name"],
    "resources": ["noteGuid", "data", "mime", "width", "height"],
    "notes": ["title", "content", "active", "notebookGuid", "tagGuids"]
}

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
        self._query("CREATE TABLE IF NOT EXISTS global_data (`key` TEXT, `value` TEXT)")
        self._query("CREATE TABLE IF NOT EXISTS tags (`local_id` INTEGER PRIMARY KEY, `guid` TEXT, name TEXT, parentGuid TEXT, updateSequenceNum NUMERIC, dirty NUMERIC DEFAULT 0, deleted NUMERIC DEFAULT 0)")
        self._query("CREATE TABLE IF NOT EXISTS notebooks (`local_id` INTEGER PRIMARY KEY, `guid` TEXT, name TEXT, updateSequenceNum NUMERIC, defaultNotebook NUMERIC DEFAULT 0, dirty NUMERIC DEFAULT 0, deleted NUMERIC DEFAULT 0)")
        self._query("CREATE TABLE IF NOT EXISTS resources (`local_id` INTEGER PRIMARY KEY, `guid` TEXT, noteGuid TEXT, data TEXT, bodyHash TEXT, mime TEXT, width NUMERIC, height NUMERIC, updateSequenceNum NUMERIC, dirty NUMERIC DEFAULT 0, deleted NUMERIC DEFAULT 0)")
        self._query("CREATE TABLE IF NOT EXISTS notes (`local_id` INTEGER PRIMARY KEY, `guid` TEXT, title TEXT, content TEXT, contentHash TEXT, contentLength NUMERIC, active NUMERIC DEFAULT 1, updateSequenceNum NUMERIC, notebookGuid TEXT, tagGuids TEXT, dirty NUMERIC DEFAULT 0, deleted NUMERIC DEFAULT 0)")
    
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
        for i in range(len(ELEMENTS_FIELDS[element_type])):
            res[ELEMENTS_FIELDS[element_type][i]] = element[i]
        return res
    
    def lookup_element_by_guid(self, element_type, guid):
        logging.debug("lookup_element_by_guid %s %s" % (element_type, guid))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        res = self._query("SELECT `" + "`, `".join(ELEMENTS_FIELDS[element_type]) + "` FROM " + element_type + " WHERE guid=?", (guid,))
        if len(res) == 1:
            return self._format_element(element_type, res[0])
    
    def lookup_element_by_name(self, element_type, name):
        logging.debug("lookup_element_by_name %s %s" % (element_type, name))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        res = self._query("SELECT " + "`" + "`, `".join(ELEMENTS_FIELDS[element_type]) + "`" + " FROM " + element_type + " WHERE name=?", (name,))
        if len(res) == 1:
            return self._format_element(element_type, res[0])
    
    def create_element_from_server(self, element_type, element):
        logging.debug("create_element_from_server %s guid %s" % (element_type, element.guid))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
            
        field_list = [field for field in ELEMENTS_FIELDS[element_type] if field not in ["local_id", "dirty", "tagGuids", "deleted"]] + ["dirty", "deleted"]
        values_list = [getattr(element, a) for a in [field for field in ELEMENTS_FIELDS[element_type] if field not in ["local_id", "dirty", "tagGuids", "deleted"]]] + [0, 0]
        
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
        
        field_list = [field for field in ELEMENTS_FIELDS[element_type] if field not in ["local_id", "dirty", "tagGuids", "deleted", "content"]] + ["dirty", "deleted"]
        query_match_array = []
        values_list = [getattr(element, a) for a in [field for field in ELEMENTS_FIELDS[element_type] if field not in ["local_id", "dirty", "tagGuids", "deleted", "content"]]] + [0, 0]
        
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
            
        elements = self._query("SELECT `" + "`, `".join(ELEMENTS_FIELDS[element_type]) + "` FROM " + element_type)
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
        
        return self._format_element(element_type, self._query("SELECT `" + "`, `".join(ELEMENTS_FIELDS[element_type]) + "` FROM " + element_type + " WHERE local_id=?", (local_id,))[0])
    
    def get_element_by_hash(self, element_type, element_hash):
        logging.debug("get_element_by_hash %s %s" % (element_type, element_hash))
        
        if not element_type in ELEMENTS_TYPES:
            logging.fatal("Unknown element type %s" % element_type)
            return
        
        return self._format_element(element_type, self._query("SELECT `" + "`, `".join(ELEMENTS_FIELDS[element_type]) + "` FROM " + element_type + " WHERE bodyHash=?", (element_hash,))[0])

class FeverAccount(EventsObject):
    def __init__(self, username):
        EventsObject.__init__(self)
        
        self._username = username
        self._account_data_file = os.path.join(os.getenv("HOME"), ".local", "share", "fever", "accounts", self._username + ".db")
        self._account_data_db = FeverAccountDB(self._account_data_file)
    
    def list_tags(self):
        return [tag for tag in self._account_data_db.list_elements("tags") if tag["deleted"] == False]
    
    def list_notebooks(self):
        return [notebook for notebook in self._account_data_db.list_elements("notebooks") if notebook["deleted"] == False]
    
    def list_notes(self):
        return [note for note in self._account_data_db.list_elements("notes") if note["deleted"] == False]
    
    def get_note(self, note_local_id):
        return self._account_data_db.get_element("notes", note_local_id)
    
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
    
    def _do_full_sync(self):
        logging.debug("_do_full_sync")
        try:
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
                            if element_type == "notes" and server_element.contentHash != client_element["contentHash"]:
                                server_element.content = noteStore.getNoteContent(server_element.guid)
                            elif element_type == "resources":
                                server_element.bodyHash = binascii.b2a_hex(server_element.data.bodyHash)
                                if server_element.data.bodyHash != binascii.b2a_hex(server_element.data.bodyHash):
                                    server_element.data = noteStore.getResourceData(server_element.guid)
                                else:
                                    server_element.data = client_element["data"]
                            self._account_data_db.update_element_from_server(element_type, client_element["local_id"], server_element)
                        elif server_element.updateSequenceNum > client_element["updateSequenceNum"] and client_element["dirty"]:
                            # Conflict
                            pass
                        elements_on_both_sides[element_type].append(client_element["local_id"])
                    else:
                        if element_type in ["tags", "notebooks"]:
                            client_element = self._account_data_db.lookup_element_by_name(element_type, server_element.name)
                        else:
                            client_element = None
                        if client_element:
                            if client_element["dirty"]:
                                # Conflict
                                pass
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
            for element_type in ELEMENTS_TYPES:
                for server_element, client_element in elements_to_upload[element_type]:
                    if client_element["updateSequenceNum"]:
                        for field in ELEMENTS_UPLOAD_FIELDS[element_type]:
                            setattr(server_element, field, client_element[field])
                        if element_type == "tags":
                            updateSequenceNum = noteStore.updateTag(server_element)
                        elif element_type == "notebooks":
                            updateSequenceNum = noteStore.updateNotebook(server_element)
                        elif element_type == "notes":
                            updateSequenceNum = noteStore.updateNote(server_element)
                        if updateSequenceNum == self.lastUpdateCount + 1:
                            self.lastUpdateCount = updateSequenceNum
                        else:
                            need_incremental_sync = True
                        self._account_data_db.update_element_from_server(element_type, client_element["local_id"], server_element)
                    else:
                        if element_type == "tags":
                            server_element = noteStore.createTag(EvernoteTypes.Tag(name = client_element["name"]))
                        elif element_type == "notebooks":
                            server_element = noteStore.createNotebook(EvernoteTypes.Notebook(name = client_element["name"]))
                        elif element_type == "notes":
                            server_element = noteStore.createNote(EvernoteTypes.Note(title = client_element["title"]))
                        self._account_data_db.update_element_from_server(element_type, client_element["local_id"], server_element)
        except:
            logging.error(sys.exc_info())
    
    def _do_sync(self):
        logging.debug("_do_sync")
        if not self.lastSyncTime:
            return self._do_full_sync()
    
    def sync(self):
        self._trigger("sync_start")
        ThreadedTask(target = self._do_sync, callback = self._on_sync_done).run()
    
    def _on_sync_done(self, response):
        logging.debug("_on_sync_done : %s" % response)
        self._trigger("sync_done")
