# Copyright (C) 2008, 2009 Sayamindu Dasgupta <sayamindu@gmail.com>
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
import gobject
import goocanvas

import math
import uuid

DEFAULT_WIDTH = 10
DEFAULT_HEIGHT = 10

CANVAS_WIDTH = 1187
CANVAS_HEIGHT = 767

class ScribbleWidget(goocanvas.Canvas):
    __gsignals__ = {
        'item-added': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([])),
    }
    def __init__(self):
        goocanvas.Canvas.__init__(self)
        self.set_size_request(CANVAS_WIDTH, CANVAS_HEIGHT)
        self.set_bounds(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)

        self.connect("button_press_event", self.on_button_press)
        self.connect("button_release_event", self.on_button_release)
        self.connect("motion_notify_event", self.on_motion)

        self._root = self.get_root_item()

        self.tool = None
        self.item = None
        self.item_id = None
        self.item_orig_x = 0
        self.item_orig_y = 0
        self.item_width = 0
        self.item_height = 0
        self.line_points = []
        self.prev_time = 0
        self._fill_color = 0
        self._stroke_color = 0
        self.cmd = None # method to draw the last item
        self.cmd_list = "" # list of methods to draw the entire canvas

    def set_fill_color(self, color):
        self._fill_color = int(color.strip('#')+'FF', 16)

    def set_stroke_color(self, color):
        self._stroke_color = int(color.strip('#')+'FF', 16)

    def set_tool(self, tool):
        self.tool = tool

    def create_item(self, x, y):
        self.item_id = str(uuid.uuid4())

        self.item_orig_x = x
        self.item_orig_y = y

        self.item_width = DEFAULT_WIDTH
        self.item_height = DEFAULT_HEIGHT

        if self.tool == 'circle':
            self.item = goocanvas.Ellipse(parent=self._root, center_x=x, \
                    center_y=y, radius_x = DEFAULT_WIDTH/2, \
                    radius_y = DEFAULT_HEIGHT/2, title=self.item_id, \
                    fill_color_rgba = self._fill_color, \
                    stroke_color_rgba = self._stroke_color)
        elif self.tool == 'rect':
            self.item = goocanvas.Rect(parent=self._root, x=x, y=y, \
                    width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, \
                    fill_color_rgba = self._fill_color, \
                    stroke_color_rgba = self._stroke_color, title=self.item_id)
        elif self.tool == 'pencil':
            self.line_points = [] #Reset
            self.line_points.append((x, y))
            self.item = goocanvas.Polyline(parent=self._root, \
                    points=goocanvas.Points(self.line_points), \
                    stroke_color_rgba = self._stroke_color, title=self.item_id)
        elif self.tool == 'poly':
            self.line_points = [] #Reset
            self.line_points.append((x, y))
            self.item = goocanvas.Polyline(parent=self._root, \
                    points=goocanvas.Points(self.line_points), \
                    stroke_color_rgba = self._stroke_color, \
                    fill_color_rgba = self._fill_color, title=self.item_id)
        elif self.tool == 'eraser':
            self.item = self.get_item_at(x, y, True)
        else:
            pass

    def process_motion(self, x, y, time):
        dx = x - self.item_orig_x
        dy = y - self.item_orig_y
        dt = time - self.prev_time

        if self.tool == 'circle':
            self.item.props.radius_x = abs(dx)
            self.item.props.radius_y = abs(dy)
        elif self.tool == 'rect':
            if dx < 0:
                self.item.props.x = x
                #self.item_orig_x = x
            if dy < 0:
                self.item.props.y = y
                #self.item_orig_y = y
            self.item.props.width = abs(dx)
            self.item.props.height = abs(dy)
        elif self.tool == 'pencil':
            #XXX: This is pretty ugly - we should try some curve fitting stuff
            dist = abs(math.sqrt(dx*dx + dy*dy))
            self.line_points.append((x, y)) 
            if dist > 10 or dt > 10:
                self.item.props.points = goocanvas.Points(self.line_points)
            self.item_orig_x = x
            self.item_orig_y = y
        elif self.tool == 'poly':
            #XXX: This is pretty ugly - we should try some curve fitting stuff
            dist = abs(math.sqrt(dx*dx + dy*dy))
            self.line_points.append((x, y)) 
            if dist > 10 or dt > 10:
                self.item.props.points = goocanvas.Points(self.line_points)
            self.item_orig_x = x
            self.item_orig_y = y
        elif self.tool == 'eraser':
            self.item = self.get_item_at(x, y, True)
        else:
            pass

        self.prev_time = time

    def get_cmd(self):
        return self.cmd

    def get_cmd_list(self):
        return self.cmd_list

    def process_item_finalize(self, x, y):
        if self.tool == 'circle':
            self.cmd = "goocanvas.Ellipse(parent=self._root, center_x=%d, \
                center_y=%d, radius_x = %d, radius_y = %d, \
                fill_color_rgba = %d, stroke_color_rgba = %d, \
                title = '%s')" % (self.item.props.center_x, \
                self.item.props.center_y, self.item.props.radius_x, \
                self.item.props.radius_y, self._fill_color, \
                self._stroke_color, self.item_id)
        elif self.tool == 'rect':
            self.cmd = "goocanvas.Rect(parent=self._root, x=%d, y=%d, \
                width=%d, height=%d, fill_color_rgba = %d, \
                stroke_color_rgba = %d, title = '%s')" % (self.item.props.x, \
                self.item.props.y, self.item.props.width, \
                self.item.props.height, self._fill_color, self._stroke_color, \
                self.item_id)
        elif self.tool == 'pencil':
            self.cmd = "goocanvas.Polyline(parent=self._root, \
                points=goocanvas.Points(%s), stroke_color_rgba = %d, \
                title = '%s')" % (str(self.line_points), self._stroke_color, \
                self.item_id)
        elif self.tool == 'poly':
            self.cmd = "goocanvas.Polyline(parent=self._root, \
                points=goocanvas.Points(%s), stroke_color_rgba = %d, \
                fill_color_rgba = %d, title = '%s')" \
                % (str(self.line_points), self._stroke_color, \
                self._fill_color, self.item_id)
        elif self.tool == 'eraser':
            if self.item is not None:
                self.item.remove()
                # Maybe we can use the item title (uuid) and use it instead
                self.cmd = "self.get_item_at(%f, %f, True).remove()" % (x, y)
            else:
                self.cmd = ''
        else:
            pass

        #print self.cmd

        if len(self.cmd_list) > 0:
            self.cmd_list += (';' + self.cmd)
        else:
            self.cmd_list = self.cmd

        self.emit('item-added')

    def process_cmd(self, cmd):
        #print 'Processing cmd :' + cmd
        exec(cmd) #FIXME: Ugly hack, but I'm too lazy to do this nicely

        if len(self.cmd_list) > 0:
            self.cmd_list += (';' + cmd)
        else:
            self.cmd_list = cmd


    def on_button_press(self, canvas, event):
        self.create_item(event.x, event.y)
        fleur = gtk.gdk.Cursor(gtk.gdk.FLEUR) 
        canvas.pointer_grab(self.item, \
            gtk.gdk.POINTER_MOTION_MASK | \
                gtk.gdk.POINTER_MOTION_HINT_MASK | gtk.gdk.BUTTON_RELEASE_MASK,
            fleur, event.time)
        return True

    def on_button_release(self, canvas, event):
        canvas.pointer_ungrab(self.item, event.time)
        self.process_item_finalize(event.x, event.y)
        return True

    def on_motion(self, canvas, event):
        if event.is_hint:
            x, y, state = event.window.get_pointer()
        else:
            x = event.x
            y = event.y
            state = event.state

        if not state & gtk.gdk.BUTTON1_MASK:
            return False

        self.process_motion(x, y, event.time)
        return True

