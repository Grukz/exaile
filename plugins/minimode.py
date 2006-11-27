#!/usr/bin/env python
# Copyright (C) 2006 Johannes Sasongko <sasongko@gmail.com>
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
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import gtk, plugins, gobject, pango
from xl import xlmisc

PLUGIN_NAME = "Mini Mode"
PLUGIN_AUTHORS = ['Adam Olsen <arolsen@gmail.com>']
PLUGIN_VERSION = '0.1'
PLUGIN_DESCRIPTION = r"""Allows for a mini mode window.\nMini Mode is activated
by pressing CTRL+ALT+M"""
PLUGIN_ENABLED = False
PLUGIN_ICON = None

PLUGIN = None
MENU_ITEM = None
ACCEL_GROUP = None
MM_ACTIVE = False

CONS = plugins.SignalContainer()

class MiniWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        self.set_title("Exaile!")
        self.set_icon(APP.window.get_icon())

        main = gtk.HBox()
        main.set_border_width(6)
        main.set_spacing(3)
        self.cover_box = gtk.EventBox()
        self.cover = xlmisc.ImageWidget()
        self.cover.set_image_size(90, 90)
        self.cover.set_image(APP.cover.loc)
        self.cover_box.connect('button_press_event', APP.cover_clicked)
        self.cover_box.add(self.cover)
        main.pack_start(self.cover_box, False)

        content_box = gtk.VBox()
        content_box.set_spacing(2)
        content_box.set_border_width(3)

        self.model = gtk.ListStore(str, object)
        self.title_box = gtk.ComboBox(self.model)
        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
    
        self.title_box.pack_start(cell, True)
        self.title_box.add_attribute(cell, 'text', 0)
        self.title_id = \
            self.title_box.connect('changed', self.change_track)

        content_box.pack_start(self.title_box)
        artist_box = gtk.HBox()

        self.artist_label = gtk.Label("Stopped")
        self.artist_label.set_alignment(0.0, 0.0)
        self.artist_label.set_ellipsize(pango.ELLIPSIZE_END)
        artist_box.pack_start(self.artist_label, True)
        self.volume_slider = gtk.HScale(gtk.Adjustment(0, 0, 120, 1, 5, 0))
        self.volume_slider.set_draw_value(False)
        self.volume_slider.set_size_request(100, -1)
        self.volume_id = self.volume_slider.connect('change-value', APP.on_volume_set)
        artist_box.pack_end(gtk.Label("+"), False)
        artist_box.pack_end(self.volume_slider, False)
        artist_box.pack_end(gtk.Label("-"), False)
        content_box.pack_start(artist_box)

        box = gtk.HBox()
        box.set_spacing(2)
        prev = self.create_button('gtk-media-previous', self.on_prev)
        box.pack_start(prev, False)
        self.play = self.create_button('gtk-media-play', self.on_play)

        box.pack_start(self.play, False)
        stop = self.create_button('gtk-media-stop', self.on_stop)
        box.pack_start(stop, False)
        next = self.create_button('gtk-media-next', self.on_next)
        box.pack_start(next, False)

        self.seeker = gtk.HScale(gtk.Adjustment(0, 0, 100, 1, 5, 0))
        self.seeker.set_draw_value(False)
        self.seeker.set_size_request(200, -1)
        self.seeker_id = self.seeker.connect('change-value', APP.seek)
        box.pack_start(self.seeker, True, True)
        self.pos_label = gtk.Label("      0:00")
        box.pack_end(self.pos_label, False)
        content_box.pack_start(box)
        self.connect('delete-event', self.on_quit)
        self.connect('configure-event', self.on_move)

        main.pack_start(content_box, True, True)

        self.add(main)
        self.set_resizable(False)
        self.first = False

    def volume_changed(self, exaile, value):
        self.volume_slider.disconnect(self.volume_id)
        self.volume_slider.set_value(value / 100.0)
        self.volume_id = self.volume_slider.connect('change-value',
            APP.on_volume_set)

    def change_track(self, combo):
        """
            Called when the user uses the title combo to pick a new song
        """
        iter = self.title_box.get_active_iter()
        if iter:
            song = self.model.get_value(iter, 1)
            APP.stop()
            APP.play_track(song)

    def setup_title_box(self):
        """
            Populates the title box and selects the currently playing track
        """
        blank = gtk.ListStore(str, object)
        self.title_box.set_model(blank)
        self.model.clear()
        count = 0
        current = APP.current_track
        if current:
            select = 0
        elif APP.songs:
            select = -1
            current = APP.songs[0] 

        if current:  
            count += 1
            self.model.append([current.title, current])

        if len(APP.songs) > 50:
            next = current

            while True:
                next = APP.tracks.get_next_track(next)
                if not next: break
                self.model.append([next.title, next])
                count += 1
                if count >= 50: break
        else:
            for song in APP.songs:
                if song == current and APP.current_track:
                    select = count
                self.model.append([song.title, song])
                count += 1

        self.title_box.set_model(self.model)
        self.title_box.disconnect(self.title_id)
        if select > -1: self.title_box.set_active(select)
        self.title_id = self.title_box.connect('changed',
            self.change_track)
        self.title_box.set_sensitive(len(self.model) > 0)

    def cover_changed(self, cover, location):
        """
            Sets the cover image, width, and height according to Exaile's
            cover image width and height
        """
        self.cover.set_image(location)

    def on_move(self, *e):
        (x, y) = self.get_position()
        settings = APP.settings
        settings['%s_x' % plugins.name(__file__)] = x
        settings['%s_y' % plugins.name(__file__)] = y

    def on_quit(self, widget=None, event=None):
        if widget == self and APP.tray_icon:
            self.hide()
            return True
        else:
            return APP.on_quit(widget, event)

    def show_window(self):
        if not self.first:
            self.first = True
            self.show_all()
        else:
            self.show()

        self.volume_slider.set_value(APP.volume.get_value())
        settings = APP.settings
        x = settings.get_int("%s_x" % plugins.name(__file__),   
            10)
        y = settings.get_int("%s_y" % plugins.name(__file__),
            10)
        self.move(x, y)
        self.setup_title_box()

    def on_prev(self, button):
        APP.on_previous()
        self.timeout_cb()

    def on_play(self, button):
        APP.toggle_pause()
        self.timeout_cb()

    def on_stop(self, button=None):
        if button: APP.stop(True)
        self.timeout_cb()
        self.play.set_image(APP.get_play_image())
        self.artist_label.set_label("Stopped")
        self.setup_title_box()
        self.artist_label.set_label("Stopped")
        self.set_title(APP.window.get_title())

    def on_next(self, button):
        APP.on_next()
        self.timeout_cb()

    def create_button(self, stock_id, func):
        """
            Creates a little button
        """
        button = gtk.Button()
        button.connect('clicked', func)
        image = gtk.Image()
        image.set_from_stock(stock_id, gtk.ICON_SIZE_SMALL_TOOLBAR)
        button.set_image(image)

        return button

    def pause_toggled(self):
        track = APP.current_track
        if not track:
            self.play.set_image(APP.get_play_image())
        else:
            if track.is_paused():
                self.play.set_image(APP.get_play_image())
            else:
                self.play.set_image(APP.get_pause_image())
        self.artist_label.set_label("by %s" % track.artist)
        self.set_title(APP.window.get_title())

    def timeout_cb(self):
        self.seeker.set_value(APP.progress.get_value())
        self.pos_label.set_label(APP.progress_label.get_label())
            
        return True

def pause_toggled(exaile, track):
    PLUGIN.pause_toggled()

def play_track(exaile, track):
    PLUGIN.pause_toggled()
    PLUGIN.setup_title_box()

def stop_track(exaile, track):
    PLUGIN.on_stop()

def toggle_minimode(*e):
    global MM_ACTIVE 
    if not PLUGIN.get_property("visible"):
        PLUGIN.show_window()
        APP.window.hide()
        MM_ACTIVE = True
    else:
        PLUGIN.hide()
        MM_ACTIVE = False
        APP.window.show()
    print "Minimode toggled"

def toggle_hide(*args):
    if not MM_ACTIVE: return False

    if PLUGIN.get_property("visible"):
        PLUGIN.hide()
    else: PLUGIN.show_window()

    return True

def pass_func(*args):
    global MM_ACTIVE 
    if PLUGIN.get_property("visible"):
        PLUGIN.hide()
        MM_ACTIVE = False
        APP.window.show()
        return True

def initialize():
    global TIMER_ID, PLUGIN, ACCEL_GROUP, MENU_ITEM

    PLUGIN = MiniWindow()
    TIMER_ID = gobject.timeout_add(1000, PLUGIN.timeout_cb)
    ACCEL_GROUP = gtk.AccelGroup()
    key, mod = gtk.accelerator_parse("<Control><Alt>M")
    ACCEL_GROUP.connect_group(key, mod, gtk.ACCEL_VISIBLE, pass_func)

    APP.window.add_accel_group(ACCEL_GROUP)
    MENU_ITEM = gtk.MenuItem("Mini Mode")
    MENU_ITEM.connect('activate', toggle_minimode)
    MENU_ITEM.add_accelerator('activate', ACCEL_GROUP, key, mod,
        gtk.ACCEL_VISIBLE)
    APP.view_menu.get_submenu().append(MENU_ITEM)
    MENU_ITEM.show()
    PLUGIN.add_accel_group(ACCEL_GROUP)
    CONS.connect(APP.cover, 'image-changed', PLUGIN.cover_changed)
    CONS.connect(APP, 'play-track', play_track)
    CONS.connect(APP, 'stop-track', stop_track)
    CONS.connect(APP, 'volume-changed', PLUGIN.volume_changed)

    if APP.tray_icon:
        CONS.connect(APP.tray_icon, 'toggle-hide', toggle_hide)
    return True

def destroy():
    global PLUGIN, MENU_ITEM, ACCEL_GROUP, MENU_ITEM, TIMER_ID

    CONS.disconnect_all()

    if TIMER_ID:
        gobject.source_remove(TIMER_ID)
        TIMER_ID = None

    if PLUGIN:
        PLUGIN.destroy()
        PLUGIN = None

    if MENU_ITEM:
        APP.view_menu.get_submenu().remove(MENU_ITEM)
        MENU_ITEM = None
        
    if ACCEL_GROUP: 
        APP.window.remove_accel_group(ACCEL_GROUP)
        ACCEL_GROUP = None
