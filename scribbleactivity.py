# Copyright 2007-2008 One Laptop Per Child
# Copyright (C) 2008, 2009 Sayamindu Dasgupta <sayamindu@gmail.com>
#
# Sharing code based on HelloMesh activity
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import logging
import telepathy

from dbus.service import method, signal
from dbus.gobject_service import ExportedGObject

from sugar import profile
from sugar.activity.activity import Activity, ActivityToolbox
import sugar.graphics.radiotoolbutton
from sugar.presence import presenceservice
from sugar.presence.tubeconn import TubeConnection

from gettext import gettext as _

from miscwidgets import ExportButton

SERVICE = "org.randomink.sayamindu.Scribble"
IFACE = SERVICE
PATH = "/org/randomink/sayamindu/Scribble"

import scribblewidget

class ScribbleActivity(Activity):
    def __init__(self, handle):
        print "running activity init", handle
        Activity.__init__(self, handle)
        print "activity running"

        self._logger = logging.getLogger('scribble-activity')        

        toolbox = ActivityToolbox(self)
        self.set_toolbox(toolbox)
        toolbox.show()

        pencilbtn = sugar.graphics.radiotoolbutton.RadioToolButton()
        pencilbtn.set_named_icon('tool-pencil')
        pencilbtn.set_tooltip(_("Pencil"))
        pencilbtn.connect('toggled', self._pencil_cb)

        circlebtn = sugar.graphics.radiotoolbutton.RadioToolButton()
        circlebtn.set_named_icon('tool-shape-ellipse')
        circlebtn.set_tooltip(_("Ellipse"))
        circlebtn.connect('toggled', self._circle_cb)
        circlebtn.set_group(pencilbtn)

        rectbtn = sugar.graphics.radiotoolbutton.RadioToolButton()
        rectbtn.set_named_icon('tool-shape-rectangle')
        rectbtn.set_tooltip(_("Rectangle"))
        rectbtn.connect('toggled', self._rect_cb)
        rectbtn.set_group(circlebtn)

        polybtn = sugar.graphics.radiotoolbutton.RadioToolButton()
        polybtn.set_named_icon('tool-shape-freeform')
        polybtn.set_tooltip(_("Shape"))
        polybtn.connect('toggled', self._poly_cb)
        polybtn.set_group(rectbtn)

        sep = gtk.SeparatorToolItem()
        sep.set_expand(False)
        sep.set_draw(True)

        erasebtn = sugar.graphics.radiotoolbutton.RadioToolButton()
        erasebtn.set_named_icon('tool-eraser')
        erasebtn.set_tooltip(_("Erase"))
        erasebtn.connect('toggled', self._erase_cb)
        erasebtn.set_group(polybtn)

        toolbar = gtk.Toolbar()
        toolbar.insert(pencilbtn, -1)
        toolbar.insert(circlebtn, -1)
        toolbar.insert(rectbtn, -1)
        toolbar.insert(polybtn, -1)
        toolbar.insert(sep, -1)
        toolbar.insert(erasebtn, -1)

        sep = gtk.SeparatorToolItem()
        sep.set_expand(True)
        sep.set_draw(False)
        toolbar.insert(sep, -1)

        exportbtn = ExportButton(self)
        toolbar.insert(exportbtn, -1)
        exportbtn.show()
        
        toolbox.add_toolbar(_('Toolbox'), toolbar)
        toolbar.show_all()

        self._scribblewidget = scribblewidget.ScribbleWidget()
        self._scribblewidget.connect('item-added', \
                self.scribblewidget_item_added_cb)
        colors = profile.get_color()
        self._scribblewidget.set_fill_color(colors.get_fill_color())
        self._scribblewidget.set_stroke_color(colors.get_stroke_color())
        self._scribblewidget.set_tool('pencil')

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self._scribblewidget)

        self.set_canvas(sw)
        sw.show_all()

        self.cmdtube = None  # Shared session
        self.initiating = False
        
        # get the Presence Service
        self.pservice = presenceservice.get_instance()
        # Buddy object for you
        owner = self.pservice.get_owner()
        self.owner = owner

        self.connect('shared', self._shared_cb)
        self.connect('joined', self._joined_cb)

    def _pencil_cb(self, button):
        if button.props.active:
            self._scribblewidget.set_tool('pencil')

    def _circle_cb(self, button):
        if button.props.active:
            self._scribblewidget.set_tool('circle')

    def _rect_cb(self, button):
        if button.props.active:
            self._scribblewidget.set_tool('rect')

    def _poly_cb(self, button):
        if button.props.active:
            self._scribblewidget.set_tool('poly')

    def _erase_cb(self, button):
        if button.props.active:
            self._scribblewidget.set_tool('eraser')

    def export(self, file_path, mimetype, options):
        window = self._scribblewidget.window
        width, height = window.get_size()
        pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB, has_alpha=False,
                                    bits_per_sample=8, width=width,
                                    height=height)
        pb.get_from_drawable(window, window.get_colormap(), 0, 0, 0, 0,
                                     width, height)

        if mimetype == 'image/jpeg':
            pb.save(file_path, 'jpeg', options)
        elif mimetype == 'image/png':
            pb.save(file_path, 'png', options)

    def write_file(self, file_path):
        f = open(file_path, 'w')
        try:
            f.write(self._scribblewidget.get_cmd_list())
        finally:
            f.close()

    def read_file(self, file_path):
        f = open(file_path, 'r')
        try:
            data = f.read()
        finally:
            f.close()

        self._scribblewidget.process_cmd(data)

    def process_cmd_cb(self, text):
        """Update Entry text when text received from others."""
        self._scribblewidget.process_cmd(text)

    def scribblewidget_item_added_cb(self, widget):
        cmd = self._scribblewidget.get_cmd()
        if self.cmdtube is not None:
            self.cmdtube.SendShape(cmd)

    def _shared_cb(self, activity):
        self._logger.debug('My activity was shared')
        self.initiating = True
        self._sharing_setup()

        self._logger.debug('This is my activity: making a tube...')
        id = self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].OfferDBusTube(
            SERVICE, {})

    def _sharing_setup(self):
        if self._shared_activity is None:
            self._logger.error('Failed to share or join activity')
            return

        self.conn = self._shared_activity.telepathy_conn
        self.tubes_chan = self._shared_activity.telepathy_tubes_chan
        self.text_chan = self._shared_activity.telepathy_text_chan

        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].connect_to_signal(
            'NewTube', self._new_tube_cb)

        self._shared_activity.connect('buddy-joined', self._buddy_joined_cb)
        self._shared_activity.connect('buddy-left', self._buddy_left_cb)

    def _list_tubes_reply_cb(self, tubes):
        for tube_info in tubes:
            self._new_tube_cb(*tube_info)

    def _list_tubes_error_cb(self, e):
        self._logger.error('ListTubes() failed: %s', e)

    def _joined_cb(self, activity):
        if not self._shared_activity:
            return

        self._logger.debug('Joined an existing shared activity')
        self.initiating = False
        self._sharing_setup()

        self._logger.debug('This is not my activity: waiting for a tube...')
        self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].ListTubes(
            reply_handler=self._list_tubes_reply_cb,
            error_handler=self._list_tubes_error_cb)

    def _new_tube_cb(self, id, initiator, type, service, params, state):
        self._logger.debug('New tube: ID=%d initator=%d type=%d service=%s '
                        'params=%r state=%d', id, initiator, type, service,
                        params, state)
        if (type == telepathy.TUBE_TYPE_DBUS and
            service == SERVICE):
            if state == telepathy.TUBE_STATE_LOCAL_PENDING:
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES].AcceptDBusTube(id)
            tube_conn = TubeConnection(self.conn,
                self.tubes_chan[telepathy.CHANNEL_TYPE_TUBES], id,
                group_iface=self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP])
            self.cmdtube = CanvasSync(tube_conn, self.initiating,
                                        self.process_cmd_cb,
                                        self._get_buddy, self._scribblewidget)

    def _buddy_joined_cb (self, activity, buddy):
        """Called when a buddy joins the shared activity.
        """
        self._logger.debug('Buddy %s joined', buddy.props.nick)

    def _buddy_left_cb (self, activity, buddy):
        """Called when a buddy leaves the shared activity.
        """
        self._logger.debug('Buddy %s left', buddy.props.nick)

    def _get_buddy(self, cs_handle):
        """Get a Buddy from a channel specific handle."""
        self._logger.debug('Trying to find owner of handle %u...', cs_handle)
        group = self.text_chan[telepathy.CHANNEL_INTERFACE_GROUP]
        my_csh = group.GetSelfHandle()
        self._logger.debug('My handle in that group is %u', my_csh)
        if my_csh == cs_handle:
            handle = self.conn.GetSelfHandle()
            self._logger.debug('CS handle %u belongs to me, %u', \
                cs_handle, handle)
        elif group.GetGroupFlags() \
            & telepathy.CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES:
            handle = group.GetHandleOwners([cs_handle])[0]
            self._logger.debug('CS handle %u belongs to %u', cs_handle, handle)
        else:
            handle = cs_handle
            self._logger.debug('non-CS handle %u belongs to itself', handle)
            # XXX: deal with failure to get the handle owner
            assert handle != 0
        return self.pservice.get_buddy_by_telepathy_handle(
            self.conn.service_name, self.conn.object_path, handle)

class CanvasSync(ExportedGObject):
    """The bit that talks over the TUBES!!!"""
    def __init__(self, tube, is_initiator, text_received_cb, get_buddy, \
            scribblewidget):
        super(CanvasSync, self).__init__(tube, PATH)
        self._logger = logging.getLogger('draw-activity.CanvasSync')
        self.tube = tube
        self.is_initiator = is_initiator
        self.text_received_cb = text_received_cb
        self.entered = False  # Have we set up the tube?
        self.text = '' # State that gets sent or received
        self._get_buddy = get_buddy  # Converts handle to Buddy object
        self._scribblewidget = scribblewidget 
        self.tube.watch_participants(self.participant_change_cb)

    def participant_change_cb(self, added, removed):
        self._logger.debug('Tube: Added participants: %r', added)
        self._logger.debug('Tube: Removed participants: %r', removed)
        for handle, bus_name in added:
            buddy = self._get_buddy(handle)
            if buddy is not None:
                self._logger.debug('Tube: Handle %u (Buddy %s) was added',
                                   handle, buddy.props.nick)
        for handle in removed:
            buddy = self._get_buddy(handle)
            if buddy is not None:
                self._logger.debug('Buddy %s was removed' % buddy.props.nick)
        if not self.entered:
            if self.is_initiator:
                self._logger.debug("I'm initiating the tube, will "
                    "watch for hellos.")
                self.add_share_init_handler()
            else:
                self.ShareInit()
        self.entered = True

    @signal(dbus_interface=IFACE, signature='')
    def ShareInit(self):
        ''' Initialize '''
        self._logger.debug('Started')

    @method(dbus_interface=IFACE, in_signature='s', out_signature='')
    def AckInit(self, text):
        """To be called on the incoming XO after they get the state"""
        if not self.text:
            self.text = text
            self._scribblewidget.process_cmd(text)
            self.add_share_init_handler()

    def add_share_init_handler(self):
        print('Adding init handler.')
        self.tube.add_signal_receiver(self.share_init_cb, 'ShareInit', IFACE,
            path=PATH, sender_keyword='sender')        
        self.tube.add_signal_receiver(self.sendshape_cb, 'SendShape', IFACE,
            path=PATH, sender_keyword='sender')

    def share_init_cb(self, sender=None):
        """The initial handshake where we send the state of the canvas"""
        if sender == self.tube.get_unique_name():
            return
        self._logger.debug('Newcomer %s has joined', sender)
        self._logger.debug('Welcoming and sending newcomer the canvas state')
        cmds = self._scribblewidget.get_cmd_list()
        self.tube.get_object(sender, PATH).AckInit(cmds,
                                                 dbus_interface=IFACE)

    def sendshape_cb(self, text, sender=None):
        """Handler for somebody sending SendShape"""
        if sender == self.tube.get_unique_name():
            # sender is my bus name, so ignore my own signal
            return
        self._logger.debug('%s sent shape %s', sender, text)
        self.text = text
        self.text_received_cb(text)

    @signal(dbus_interface=IFACE, signature='s')
    def SendShape(self, text):
        """Send some Shape instruction to all participants."""
        self.text = text
