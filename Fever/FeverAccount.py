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
from gi.repository import GObject

from evernote.api.client import EvernoteClient
from evernote.edam.notestore import NoteStore
from evernote.edam.type import ttypes as EvernoteTypes

class FeverAccountDB(object):
    def __init__(self, db_file):
        self._db_file = db_file
        if not os.path.exists(os.path.split(self._db_file)[0]):
            fsutils.rec_mkdir(os.path.split(self._db_file)[0])
        self._db = sqlite3.Connection(self._db_file)
        
        self._main_thread = threading.current_thread()
        
        self._query_lock = threading.Lock()
        self._query_id = 0
        self._query_queue = {}
        self._query_results = {}
        
        GObject.timeout_add(10, self._check_query_queue)
        
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
        self._query("CREATE TABLE IF NOT EXISTS tags (`local_id` INTEGER PRIMARY KEY, `guid` TEXT, name TEXT, parentGuid TEXT, updateSequenceNum NUMERIC, dirty NUMERIC DEFAULT 0)")
        self._query("CREATE TABLE IF NOT EXISTS notebooks (`local_id` INTEGER PRIMARY KEY, `guid` TEXT, name TEXT, updateSequenceNum NUMERIC, defaultNotebook NUMERIC DEFAULT 0, dirty NUMERIC DEFAULT 0)")
    
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
    
    def lookup_tag_by_guid(self, guid):
        logging.debug("lookup_tag_by_guid %s" % guid)
        res = self._query("SELECT * FROM tags WHERE guid=?", (guid,))
        if len(res) == 1:
            return {
                "local_id": res[0][0],
                "guid": res[0][1],
                "name": res[0][2],
                "parentGuid": res[0][3],
                "updateSequenceNum": res[0][4],
                "dirty": res[0][5]
            }
    
    def lookup_tag_by_name(self, name):
        logging.debug("lookup_tag_by_name %s" % name)
        res = self._query("SELECT * FROM tags WHERE name=?", (name,))
        if len(res) == 1:
            return {
                "local_id": res[0][0],
                "guid": res[0][1],
                "name": res[0][2],
                "parentGuid": res[0][3],
                "updateSequenceNum": res[0][4],
                "dirty": res[0][5]
            }
    
    def create_tag_from_server(self, tag):
        logging.debug("create_tag_from_server guid %s, name %s", tag.guid, tag.name)
        self._query("INSERT INTO tags (guid, name, parentGuid, updateSequenceNum, dirty) VALUES (?, ?, ?, ?, 0)", (tag.guid, tag.name, tag.parentGuid, tag.updateSequenceNum))
    
    def update_tag_from_server(self, local_id, tag):
        logging.debug("update_tag_from_server guid %s, name %s", tag.guid, tag.name)
        self._query("UPDATE tags SET guid=?, name=?, parentGuid=?, updateSequenceNum=?, dirty=0 WHERE local_id=?", (tag.guid, tag.name, tag.parentGuid, tag.updateSequenceNum, local_id))
    
    def list_tags(self):
        tags = self._query("SELECT * FROM tags")
        res = []
        for tag in tags:
            res.append({
                "local_id": tag[0],
                "guid": tag[1],
                "name": tag[2],
                "parentGuid": tag[3],
                "updateSequenceNum": tag[4],
                "dirty": tag[5]
            })
        return res
    
    def delete_tag(self, local_id):
        logging.debug("delete_tag %d", local_id)
        self._query("DELETE FROM tags WHERE local_id=?", (local_id,))
    
    def rename_tag(self, local_id, new_name):
        self._query("UPDATE tags SET name=?, dirty=1 WHERE local_id=?", (new_name, local_id))
        
    def lookup_notebook_by_guid(self, guid):
        logging.debug("lookup_notebook_by_guid %s" % guid)
        res = self._query("SELECT * FROM notebooks WHERE guid=?", (guid,))
        if len(res) == 1:
            return {
                "local_id": res[0][0],
                "guid": res[0][1],
                "name": res[0][2],
                "updateSequenceNum": res[0][3],
                "defaultNotebook": res[0][4],
                "dirty": res[0][5]
            }
    
    def lookup_notebook_by_name(self, name):
        logging.debug("lookup_notebook_by_name %s" % name)
        res = self._query("SELECT * FROM notebooks WHERE name=?", (name,))
        if len(res) == 1:
            return {
                 "local_id": res[0][0],
                "guid": res[0][1],
                "name": res[0][2],
                "updateSequenceNum": res[0][3],
                "defaultNotebook": res[0][4],
                "dirty": res[0][5]
            }
    
    def create_notebook_from_server(self, notebook):
        logging.debug("create_notebook_from_server guid %s, name %s", notebook.guid, notebook.name)
        self._query("INSERT INTO notebooks (guid, name, updateSequenceNum, defaultNotebook, dirty) VALUES (?, ?, ?, ?, 0)", (notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.defaultNotebook))
    
    def update_notebook_from_server(self, local_id, notebook):
        logging.debug("update_notebook_from_server guid %s, name %s", notebook.guid, notebook.name)
        self._query("UPDATE notebooks SET guid=?, name=?, updateSequenceNum=?, defaultNotebook=?, dirty=0 WHERE local_id=?", (notebook.guid, notebook.name, notebook.updateSequenceNum, notebook.defaultNotebook, local_id))
    
    def list_notebooks(self):
        notebooks = self._query("SELECT * FROM notebooks")
        res = []
        for notebook in notebooks:
            res.append({
                "local_id": notebook[0],
                "guid": notebook[1],
                "name": notebook[2],
                "updateSequenceNum": notebook[3],
                "defaultNotebook": notebook[4],
                "dirty": notebook[5]
            })
        return res
    
    def delete_notebook(self, local_id):
        logging.debug("delete_notebook %d", local_id)
        self._query("DELETE FROM notebooks WHERE local_id=?", (local_id,))
    
    def rename_notebook(self, local_id, new_name):
        self._query("UPDATE notebooks SET name=?, dirty=1 WHERE local_id=?", (new_name, local_id))

class FeverAccount(EventsObject):
    def __init__(self, username):
        EventsObject.__init__(self)
        
        self._username = username
        self._account_data_file = os.path.join(os.getenv("HOME"), ".local", "share", "fever", "accounts", self._username + ".db")
        self._account_data_db = FeverAccountDB(self._account_data_file)
    
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
                #~ "includeNotes": True,
                "includeTags": True,
                "includeNotebooks": True,
                #~ "includeNoteResources": True,
                #~ "includeNoteAttributes": True,
                #~ "includeResources": True,
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
            
            tags_list = []
            notebooks_list = []
            for chunk in chunks_list:
                if chunk.tags:
                    tags_list += chunk.tags
                if chunk.notebooks:
                    notebooks_list += chunk.notebooks
            
            # Tags sync
            tags_to_upload = []
            tags_on_both_sides = []
            created_tags = []
            for server_tag in tags_list:
                client_tag = self._account_data_db.lookup_tag_by_guid(server_tag.guid)
                if client_tag:
                    if server_tag.updateSequenceNum == client_tag["updateSequenceNum"] and not client_tag["dirty"]:
                        # Nothing to do, tag is in sync
                        pass
                    elif server_tag.updateSequenceNum == client_tag["updateSequenceNum"] and client_tag["dirty"]:
                        tags_to_upload.append((server_tag, client_tag))
                    elif server_tag.updateSequenceNum > client_tag["updateSequenceNum"] and not client_tag["dirty"]:
                        self._account_data_db.update_tag_from_server(client_tag["local_id"], server_tag)
                    elif server_tag.updateSequenceNum > client_tag["updateSequenceNum"] and client_tag["dirty"]:
                        # Conflict
                        pass
                    tags_on_both_sides.append(client_tag["local_id"])
                else:
                    client_tag = self._account_data_db.lookup_tag_by_name(server_tag.name)
                    if client_tag:
                        if client_tag["dirty"]:
                            # Conflict
                            pass
                        else:
                            index = 2
                            new_name = "%s (%n)" % (client_tag["name"], index)
                            while self._account_data_db.lookup_tag_by_name(new_name):
                                index += 1
                                new_name = "%s (%n)" % (client_tag["name"], index)
                            self._account_data_db.rename_tag(client_tag["local_id"], new_name)
                    else:
                        self._account_data_db.create_tag_from_server(server_tag)
                        created_tags.append(server_notebook.guid)
            
            for client_tag in self._account_data_db.list_tags():
                if not client_tag["local_id"] in tags_on_both_sides and not client_tag["guid"] in created_tags:
                    if client_tag["dirty"] == 0 or client_tag["updateSequenceNum"]:
                        self._account_data_db.delete_tag(client_tag["local_id"])
                    else:
                        tags_to_upload.append((None, client_tag))
            
            # Notebooks sync
            notebooks_to_upload = []
            notebooks_on_both_sides = []
            created_notebooks = []
            for server_notebook in notebooks_list:
                client_notebook = self._account_data_db.lookup_notebook_by_guid(server_notebook.guid)
                if client_notebook:
                    if server_notebook.updateSequenceNum == client_notebook["updateSequenceNum"] and not client_notebook["dirty"]:
                        # Nothing to do, notebook is in sync
                        pass
                    elif server_notebook.updateSequenceNum == client_notebook["updateSequenceNum"] and client_notebook["dirty"]:
                        notebooks_to_upload.append((server_notebook, client_notebook))
                    elif server_notebook.updateSequenceNum > client_notebook["updateSequenceNum"] and not client_notebook["dirty"]:
                        self._account_data_db.update_notebook_from_server(client_notebook["local_id"], server_notebook)
                    elif server_notebook.updateSequenceNum > client_notebook["updateSequenceNum"] and client_notebook["dirty"]:
                        # Conflict
                        pass
                    notebooks_on_both_sides.append(client_notebook["local_id"])
                else:
                    client_notebook = self._account_data_db.lookup_notebook_by_name(server_notebook.name)
                    if client_notebook:
                        if client_notebook["dirty"]:
                            # Conflict
                            pass
                        else:
                            index = 2
                            new_name = "%s (%n)" % (client_notebook["name"], index)
                            while self._account_data_db.lookup_notebook_by_name(new_name):
                                index += 1
                                new_name = "%s (%n)" % (client_notebook["name"], index)
                            self._account_data_db.rename_notebook(client_notebook["local_id"], new_name)
                    else:
                        self._account_data_db.create_notebook_from_server(server_notebook)
                        created_notebooks.append(server_notebook.guid)
            
            for client_notebook in self._account_data_db.list_notebooks():
                if not client_notebook["local_id"] in notebooks_on_both_sides and not client_notebook["guid"] in created_notebooks:
                    if client_notebook["dirty"] == 0 or client_notebook["updateSequenceNum"]:
                        self._account_data_db.delete_notebook(client_notebook["local_id"])
                    else:
                        notebooks_to_upload.append((None, client_notebook))
            
            #~ self.lastUpdateCount = chunk.updateCount
            #~ self.lastSyncTime = chunk.currentTime
            
            need_incremental_sync = False
            
            # Tags upload
            for server_tag, client_tag in tags_to_upload:
                if client_tag["updateSequenceNum"]:
                    server_tag.name = client_tag["name"]
                    updateSequenceNum = noteStore.updateTag(server_tag)
                    if updateSequenceNum == self.lastUpdateCount + 1:
                        self.lastUpdateCount = updateSequenceNum
                    else:
                        need_incremental_sync = True
                    self._account_data_db.update_tag_from_server(client_tag["local_id"], server_tag)
                else:
                    server_tag = noteStore.createTag(EvernoteTypes.Tag(name = client_tag["name"]))
                    self._account_data_db.update_tag_from_server(client_tag["local_id"], server_tag)
            
            # Notebooks upload
            for server_notebook, client_notebook in notebooks_to_upload:
                if client_notebook["updateSequenceNum"]:
                    server_notebook.name = client_notebook["name"]
                    updateSequenceNum = noteStore.updateNotebook(server_notebook)
                    if updateSequenceNum == self.lastUpdateCount + 1:
                        self.lastUpdateCount = updateSequenceNum
                    else:
                        need_incremental_sync = True
                    self._account_data_db.update_notebook_from_server(client_notebook["local_id"], server_notebook)
                else:
                    server_notebook = noteStore.createNotebook(EvernoteTypes.Notebook(name = client_notebook["name"]))
                    self._account_data_db.update_notebook_from_server(client_notebook["local_id"], server_notebook)
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
