#!/usr/bin/python
# -*- mode:python; tab-width:4; indent-tabs-mode:t; -*-
# datamanager.py
#
# provides utility to manage datastore locally and on schoolserver
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301

from sugar.activity import activity
from sugar.datastore import datastore
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.menuitem import MenuItem

import os, sys, time
import subprocess

import pygtk
pygtk.require('2.0')
import gtk

from path import path
from datetime import datetime
from time import strftime

import urllib2
from BeautifulSoup import BeautifulSoup

ACTIVITYPATH = path(activity.get_bundle_path())
DATAPATH = path(activity.get_activity_root()) / "data"
WORKPATH = DATAPATH / 'work'
KEYPATH = ACTIVITYPATH / '.ssh'
STOREPATH = path("/library/Datastore")
COMMONSPATH = path("/library/Commons")
LOCALPATH = path("/home/olpc/.sugar/default/datastore/store")
DATEFORMAT = "%Y-%m-%d %H:%M:%S"

ACTIVITYTOOLBAR = 0
USAGETOOLBAR = 1
DEFAULTTOOLBAR = ACTIVITYTOOLBAR

class DataManager(activity.Activity):

    def __init__(self, handle):

        global store
        global SERIALNUMBER
        global quitflag

        activity.Activity.__init__(self, handle)
        self.set_title("Datamanager")
        f = open('/ofw/serial-number', 'r')
        t = f.read()
        f.close()
        SERIALNUMBER = t[:11]
        print 'serial-number', SERIALNUMBER
        quitflag = False
        subprocess.call("mkdir -p " + WORKPATH, shell=True)
        #Create the usage toolbar
        self.usageTB = UsageToolbar(self)
        #Create the standard activity toolbox
        toolbox = activity.ActivityToolbox(self)
        toolbox.add_toolbar("Usage", self.usageTB)
        toolbox.set_current_toolbar(DEFAULTTOOLBAR)
        self.set_toolbox(toolbox)
        toolbox.show()
        self.viewer = Listview()
        #set up main screen
        self.main_screen = gtk.VBox()
        self.main_screen.pack_start(self.viewer, True, True, 0)
        self.set_canvas(self.main_screen)
        print 'canvas set'
        self.show_all()
        self.viewer.set_label('canvas set')
        treeView = self.viewer.get_treeView()
        treeView.set_model(self.viewer.create_model(self.usageTB))
        txt = 'ready: ' + str(len(store)) + ' documents '
        txt = txt + str(MB) + '/1000 ' + str(PCT) + '%'
        self.viewer.set_label(txt)

    def write_file(self, file_path):
        global SERIALNUMBER
        global store
        global online
        global quitflag
        f = open(file_path, 'w')
        f.write('this is a dummy file')
        f.close()
        if quitflag:
            return
        else:
            quitflag = True
        action_request = 5
        status = 4
        today = strftime(DATEFORMAT)[:10]
        if online:
            self.viewer.set_label('closing - online')
            print 'can_close online'
        #now the real work begins
        remove_list =  []
        wcount = 0
        acount = 0
        for row in store:
            self.viewer.set_label('reviewing status: ' + row[0])
            #action_request = 0: no action
            #action_request = +2: download
            #action_request = +1: upload
            #action_request = -1: remove
            if row[status] == 'White':
               print 'today', today, 'mtime', row[3]
               if row[3].find(today) < 0:
                   row[action_request] = -1
                   wcount += 1
            if row[status] == 'Red':
               row[action_request] = +1
            if row[action_request] < 0:
               acount += 1
               remove_list.append(row[0])
            if online:
               if row[action_request] == 1 and row[status] == 'Red':
                   #upload it
                   self.viewer.set_label('reviewing status: ' + row[0] + ' upload')
                   mname = row[0] + '.metadata'
                   fname = row[0]
                   srcm = LOCALPATH / mname
                   srcf = LOCALPATH / fname
                   if srcm.exists() and srcf.exists():
                       pfx = SERIALNUMBER + '@schoolserver:'
                       dst = STOREPATH / SERIALNUMBER
                       cmd = 'scp ' + srcm + ' ' + pfx + dst
                       print 'metadata upload', cmd
                       subprocess.call(cmd, shell=True)
                       cmd = 'scp ' + srcf + ' ' + pfx + dst
                       print 'file upload', cmd
                       subprocess.call(cmd, shell=True)
                   else:
                       print 'upload request but no document', row[1], srcf
               if row[action_request] > 1 and row[status] == "Green":
                   #download from schoolserver
                   self.viewer.set_label('reviewing status: ' + row[0] + ' download')
                   mname = row[0] + '.metadata'
                   fname = row[0]
                   dst = LOCALPATH
                   pfx = SERIALNUMBER + '@schoolserver:'
                   src = STOREPATH / SERIALNUMBER / mname
                   cmd = 'scp ' + pfx + src + ' ' + dst
                   print 'metadata download', cmd
                   subprocess.call(cmd, shell=True)
                   src = STOREPATH / SERIALNUMBER / fname
                   cmd = 'scp ' + pfx + src + ' ' + dst
                   print 'file download', cmd
                   subprocess.call(cmd, shell=True)
               if row[action_request] > 1 and row[status] == "cyan":
                   #download from Commons
                   self.viewer.set_label('reviewing status: ' + row[0] + ' download')
                   #if mime_type is activity - install it
                   mname = row[0] + '.metadata'
                   fname = row[0]
                   dst = LOCALPATH
                   pfx = SERIALNUMBER + '@schoolserver:'
                   src = COMMONSPATH / mname
                   cmd = 'scp ' + pfx + src + ' ' + dst
                   print 'metadata download', cmd
                   subprocess.call(cmd, shell=True)
                   src = COMMONSPATH / fname
                   cmd = 'scp ' + pfx + src + ' ' + dst
                   print 'file download', cmd
                   subprocess.call(cmd, shell=True)
               if row[action_request] == 1 and row[status] == 'cyan':
                   #upload entry to Commons
                   self.viewer.set_label('reviewing status: ' + row[0] + ' upload')
                   #if mime_type is activity - install it
                   mname = row[0] + '.metadata'
                   fname = row[0]
                   dst = COMMONSPATH / mname
                   pfx = SERIALNUMBER + '@schoolserver:'
                   src = LOCALPATH / mname
                   cmd = 'scp '  + src + ' ' + pfx + dst
                   print 'metadata  upload', cmd
                   subprocess.call(cmd, shell=True)
                   src = LOCALPATH / fname
                   cmd = 'scp ' + src + ' ' + pfx + dst
                   print 'file upload', cmd
                   subprocess.call(cmd, shell=True)
        #now remove
        self.viewer.set_label('removing files ...')
        print 'removing:' , len(remove_list)
        print 'white entries:', wcount
        print 'appended:', acount
        count = 0
        for obj in remove_list:
            ds_object = datastore.get(obj)
            if ds_object:
                ds_object.destroy()
                datastore.delete(ds_object.object_id)
                count += 1
            else:
                print 'obj not found', obj
        txt = 'done ' + str(count) + ' files deleted'
        self.viewer.set_label(txt)
        print txt

    def show_properties(self, widget):
        treeView = self.viewer.get_treeView()
        treeselection = treeView.get_selection()
        model, row = treeselection.get_selected()
        obj = model[row][0]
        fn = obj + '.metadata'
        pth = LOCALPATH / fn
        print 'on_activated:', pth
        f = open(pth,'r')
        metadata = eval(f.read())
        f.close()

        tstr = ""
        for k, v in metadata.iteritems():
            try:
                if len(str(v)) > 0:
                    tstr = tstr + k + ':' + v + '\n'
            except:
                tstr = tstr + k + ':' + "" + '\n'
        self.viewer.label.set_text(tstr)

    def upload_commons(self, widget):
        treeView = self.viewer.get_treeView()
        treeselection = treeView.get_selection()
        model, selection = treeselection.get_selected()
        row = model[selection]
        if row[4] == 'Green':
            row[4] = 'cyan'
            row[5] = 1

    def delete_entry(self, widget):
        treeView = self.viewer.get_treeView()
        treeselection = treeView.get_selection()
        model, selection = treeselection.get_selected()
        row = model[selection]
        ds_object = datastore.get(row[0])
        ds_object.destroy()
        datastore.delete(ds_object.object_id)
        model.remove(selection)

# based on PyGTK tutorial by jan bodnar, zetcode.com, February 2009
class Listview(gtk.VBox):
    def __init__(self):
        global online
        print 'Listview init'
        gtk.VBox.__init__(self)
        self.connect("destroy", gtk.main_quit)
        self.online = False
        online = False
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.treeView = gtk.TreeView()
        self.treeView.connect("row-activated", self.on_activated)
        self.treeView.set_rules_hint(True)
        self.treeView.show_all()
        sw.add(self.treeView)

        print 'create_columns'
        self.create_columns(self.treeView)
        print 'pack sw'
        self.pack_start(sw, True, True, 0)

        print 'set up metadata display'
        self.label = gtk.Label("")
        self.label.show()
        self.frame = gtk.Frame(label='Status')
        self.frame.add(self.label)
        self.frame.show()
        self.pack_start(self.frame, False, False, 0)
        print 'show all'
        self.show_all()

    def get_treeView(self):
        return self.treeView

    def set_label(self, txt):
        self.label.set_text(txt)
        while gtk.events_pending():
           gtk.main_iteration(False)

    def create_model(self, tb):
        global online
        global store
        global SERIALNUMBER
        action_request = 5
        status = 4
        #object is object_id, str = title, str = mime_type or activity,
        #str is color of col 1 (status), str is source color of col 0 (source)
        store = gtk.ListStore(object, str, str, str, str, int)
        #let's display objects from the schoolserver
        #temp for testing
        url = "http://schoolserver/Commons/"
        try:
            response = urllib2.urlopen(url)
        except:
            response = None
        if response:
            self.online = True
            online = True
            self.addentries(store, response, "cyan")
        url = "http://schoolserver/Datastore/" + SERIALNUMBER
        try:
            response = urllib2.urlopen(url)
        except:
            response = None
        if response:
            self.online = True
            online = True
            self.addentries(store, response, "light green")
        if self.online:
            print 'online'
        else:
            tb.item2.remove(tb.fuelguage2)
            tb.lbl2.set_text("not connected")
        #objects from the local datastore
        #new strategy - get directly - not through datastore
        #we want to compare items in store with items in LOCALPATH
        #if there is a match - set status
        storelist = []
        for row in store:
            storelist.append(row[0])
            fn = row[0] + '.metadata'
            pth = LOCALPATH / fn
            if pth.exists():
                if row[status] == 'cyan':
                    row[status] = 'Blue'
                else:
                    row[status] = 'Green'
        for f in LOCALPATH.files():
            #is this file already on the schoolserver?
            if f.namebase not in storelist and f.ext == '.metadata':
               m = open(f, 'r')
               mstr = m.read()
               m.close()
               try:
                   metadata = eval(mstr)
               except:
                   metadata = {}
                   print 'metadata eval failed', sys.exc_info()[0]
               obj = f.namebase
               try:
                   title = metadata['title']
               except:
                   try:
                       title = metadata['title:text']
                   except:
                       title = 'not given'
               try:
                   mime_type = metadata['mime_type']
               except:
                   mime_type = ''
               if len(mime_type) <= 0:
                   try:
                        mime_type = metadata['activity']
                   except:
                        mime_type = 'not given'
               try:
                   mtime = metadata['mtime']
               except:
                   mtime = ""
               #tm = datetime.fromtimestamp(mtime)
               #date = tm.strftime(DATEFORMAT)
               temp = mtime.replace('T',' ')
               pos = mtime.find('.')
               date = temp[:pos]
               fpath = LOCALPATH / obj
               if fpath.exists():
                  color = 'Red'
                  if mime_type == 'application/zip':
                     fn = metadata['filename']
                     if fn.find('.smxo') > 0:
                         mime_type = 'application/x-smile'
                     if fn.find('.cpxo') > 0:
                         mime_type = 'application/x-classroompresenter'
                     if fn.find('.iqxo') > 0:
                         mime_type = 'application/x-imagequiz'
                     if not mime_type == 'application/zip':
                         metadata['mime_type'] = mime_type
                         mstr = repr(metadata)
                         m = open(f, 'w')
                         m.write(mstr)
                         m.close()
                  if metadata['activity'] == 'org.olenepal.DataManager':
                         color = 'White'
               else:
                  color = 'White'
               store.append([obj, title, mime_type, date, color, 0])

        store.set_sort_column_id(3, gtk.SORT_DESCENDING)
        print 'return store'
        return store

    def addentries(self, store, response, source):
        global SERIALNUMBER
        print 'addentries:', SERIALNUMBER, source
        treeView = self.get_treeView()
        soup = BeautifulSoup(response)
        entry_candidates = soup.findAll('a')
        if source == "Blue":
            base = COMMONSPATH
        else:
            base = STOREPATH / SERIALNUMBER
        for entry in entry_candidates:
            t = str(entry)
            pos = t.find('metadata')
            if pos > 0:
                pos2 = t.find('href=')
                obj = t[pos2+6:pos-1]
                fn = t[pos2+6:pos+8]
                pth = base / fn
                cmd = "scp " + SERIALNUMBER + "@schoolserver:" + pth
                cmd = cmd + " " + WORKPATH
                subprocess.call(cmd, shell=True)
                pth = WORKPATH / fn
                if pth.exists():
                    f = open(pth, 'r')
                    t = f.read()
                    f.close()
                else:
                    print 'addentries: no f', f.name
                subprocess.call("rm -rf pth", shell=True)
                try:
                    metadata = eval(t)
                except:
                    print 'addentries eval failed', sys.exc_info()[0]
                    print 'addentries eval failed', f.name
                    print 'addentries eval failed', len(t), t
                    metadata = {}
                try:
                    title = metadata['title']
                except:
                    try:
                        title = metadata['title:text']
                    except:
                        title = ''
                try:
                    mime_type = metadata['mime_type']
                except:
                    mime_type = ""
                try:
                    mtime = metadata['mtime'].replace('T',' ')
                    pos = mtime.find('.')
                    date = mtime[:pos]
                except:
                    date = ""
                store.append([obj, title, mime_type, date, source, 0])
                treeView.set_model(store)
                treeView.scroll_to_cell(len(store)-1)
                self.set_label(title)

    def create_columns(self, treeView):

        status = 4
        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Title", rendererText, text=1)
        column.add_attribute(rendererText, "cell-background", status)
        column.set_sort_column_id(1)
        treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Mime_type", rendererText, text=2)
        column.set_sort_column_id(2)
        treeView.append_column(column)

        rendererText = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Date", rendererText, text=3)
        column.set_sort_column_id(3)
        treeView.append_column(column)

    def on_activated(self, widget, selection, col):

        #what we really want to do
        #is define a request to upload/remove/download an entry
        model = widget.get_model()
        row = model[selection]
        row4 = row[4]
        row5 = row[5]
        if row[4] == 'light green':
            row[4] = 'Green'
            row[5] = 2
        elif row[4] == 'cyan':
            row[4] = 'Blue'
            row[5] = 2
        elif row[4] == 'Green':
            row[4] = 'light green'
            row[5] = -1
        elif row[4] == 'Blue':
            row[4] = 'cyan'
            row[5] = -1
        print 'on_activiated', row[1], row4, '->', row[4], row5, '->', row[5]

class UsageToolbar(gtk.Toolbar):

    def __init__(self, activity):
        global SERIALNUMBER
        global MB
        global PCT
        gtk.Toolbar.__init__(self)

        self.lbl1 = gtk.Label("XO  ")
        self.lbl1.show()
        self.item0 = gtk.ToolItem()
        self.item0.add(self.lbl1)
        self.insert(self.item0, -1)

        self.fuelguage1 = gtk.ProgressBar(adjustment=None)
        style = self.fuelguage1.get_style().copy()
        style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse('White')
        style.bg[gtk.STATE_PRELIGHT] = gtk.gdk.color_parse('Red')
        self.fuelguage1.set_style(style)
        cmd = 'du -h /home/olpc/.sugar/default/datastore > /tmp/rslt'
        #need way to return stdout to get rslt
        subprocess.call(cmd, shell=True)
        f = open('/tmp/rslt','r')
        storesize = f.read()
        f.close()
        print 'du datastore', len(storesize), storesize
        cmd = 'df -h > /tmp/rslt1'
        subprocess.call(cmd, shell=True)
        f = open('/tmp/rslt1', 'r')
        t = f.read()
        f.close()
        print 'df', len(t), t
        totalsize = t.split('\n')
        t1 = totalsize[1]
        pos = t1.find('M')
        MB = t1[pos-4:pos].strip()
        pos = t1.find('%')
        rslt = t1[pos-4:pos].strip()
        print 'rslt', float(rslt) * .01
        PCT = rslt
        self.fuelguage1.set_fraction(float(rslt) * .01)
        self.fuelguage1.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
        self.fuelguage1.show()
        self.item1 = gtk.ToolItem()
        self.item1.add(self.fuelguage1)
        self.insert(self.item1, -1)

        self.spacer = gtk.ToolItem()
        self.spacer.set_expand(True)
        self.insert(self.spacer, -1)

        self.lbl2 = gtk.Label("Schoolserver  ")
        self.lbl2.show()
        self.item3 = gtk.ToolItem()
        self.item3.add(self.lbl2)
        self.insert(self.item3, -1)

        self.fuelguage2 = gtk.ProgressBar(adjustment=None)
        style = self.fuelguage2.get_style().copy()
        style.bg[gtk.STATE_NORMAL] = gtk.gdk.color_parse('White')
        style.bg[gtk.STATE_PRELIGHT] = gtk.gdk.color_parse('Red')
        self.fuelguage2.set_style(style)
        #need a way to know if schoolserver not online
        #need a way to return rslt from stdout
        cmd = "ssh -i " + KEYPATH + SERIALNUMBER + "@schoolserver "
        cmd = cmd + "du -h /library/datastore/" + SERIALNUMBER
        #subprocess.call(cmd, shell=True)
        rslt = 0.1
        self.fuelguage2.set_fraction(rslt)
        self.fuelguage2.set_orientation(gtk.PROGRESS_LEFT_TO_RIGHT)
        self.item2 = gtk.ToolItem()
        self.item2.add(self.fuelguage2)
        self.insert(self.item2, -1)

        self.__infobtn = ToolButton('info')
        self.__infobtn.set_tooltip("Show properties")
        self.__infobtn.connect('clicked', activity.show_properties)
        self.insert(self.__infobtn, -1)
        self.__infobtn.show()

        self.__uploadbtn = ToolButton('up_arrow')
        self.__uploadbtn.set_tooltip("Upload document to Commons")
        self.__uploadbtn.connect('clicked', activity.upload_commons)
        self.insert(self.__uploadbtn, -1)
        self.__uploadbtn.show()

        self.__deletebtn = ToolButton('stock_delete')
        self.__deletebtn.set_tooltip("Delete entry from local store")
        self.__deletebtn.connect('clicked', activity.delete_entry)
        self.insert(self.__deletebtn, -1)
        self.__deletebtn.show()
