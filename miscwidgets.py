# Originally part of Write Activity
# Modified by Sayamindu Dasgupta <sayamindu@laptop.org>

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

import os
import time
from gettext import gettext as _
import logging

import gobject 

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.menuitem import MenuItem
from sugar.datastore import datastore

logger = logging.getLogger('scribble-activity')

class ExportButton(ToolButton):
    _EXPORT_FORMATS = [{'mime_type' : 'image/jpeg',
                        'title'     : _('JPEG'),
                        'exp_props' : {"quality":"85"}},

                       {'mime_type' : 'image/png',
                        'title'     : _('PNG'),
                        'exp_props' : {}}]

    def __init__(self, activity):
        ToolButton.__init__(self, 'document-save')
        self.props.tooltip = _('Export')
        self.props.label = _('Export')
        self._activity = activity

        for i in self._EXPORT_FORMATS:
            menu_item = MenuItem(i['title'])
            menu_item.connect('activate', self.__activate_cb, activity, i)
            self.props.palette.menu.append(menu_item)
            menu_item.show()

        self.connect('clicked', self._clicked_cb)

    def _clicked_cb(self, widget):
        self._export(self._activity, self._EXPORT_FORMATS[0])
        
    #def do_clicked(self):
    #    self._export(self._activity, _EXPORT_FORMATS[0])

    def _export(self, activity, fmt):
        exp_props = fmt['exp_props']

        # create a new journal item
        fileObject = datastore.create()
        act_meta = activity.metadata
        fileObject.metadata['title'] = \
                _('Exported image from %s') % (act_meta['title'])
        fileObject.metadata['title_set_by_user'] = \
                act_meta['title_set_by_user']
        fileObject.metadata['mime_type'] = fmt['mime_type']

        fileObject.metadata['icon-color'] = act_meta['icon-color']
        fileObject.metadata['keep'] = act_meta['keep']

        #fileObject.metadata['share-scope'] = act_meta['share-scope']

        # write out the document contents in the requested format
        fileObject.file_path = os.path.join(activity.get_activity_root(),
                'instance', '%i' % time.time())
        activity.export(fileObject.file_path, fmt['mime_type'], \
                exp_props)

        # store the journal item
        datastore.write(fileObject, transfer_ownership=True)
        fileObject.destroy()
        del fileObject

        return False

    def __activate_cb(self, menu_item, activity, fmt):
        logger.debug('exporting file: %r' % fmt)

        gobject.timeout_add_seconds(1, self._export, activity, fmt)
