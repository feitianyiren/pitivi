# PiTiVi , Non-linear video editor
#
#       pitivi/medialibrary.py
#
# Copyright (c) 2012, Matas Brazdeikis <matas@brazdeikis.lt>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 51 Franklin St, Fifth Floor,
# Boston, MA 02110-1301, USA.

"""
Shows title editor
"""
import os
import gtk
import pango
import ges
import gst
import gobject

from gettext import gettext as _
from xml.sax import saxutils

from utils.timeline import SELECT
from pitivi.configure import get_ui_dir, get_pixmap_dir
from pitivi.utils.loggable import Loggable
from pitivi.utils.signal import Signallable
from pitivi.utils.pipeline import Seeker
INVISIBLE = gtk.gdk.pixbuf_new_from_file(os.path.join(get_pixmap_dir(), "invisible.png"))


class PangoBuffer(gtk.TextBuffer):
    desc_to_attr_table = {
        'family': [pango.AttrFamily, ""],
        'size': [pango.AttrSize, 14 * 1024],
        'style': [pango.AttrStyle, pango.STYLE_NORMAL],
        'variant': [pango.AttrVariant, pango.VARIANT_NORMAL],
        'weight': [pango.AttrWeight, pango.WEIGHT_NORMAL],
        'stretch': [pango.AttrStretch, pango.STRETCH_NORMAL]}
    # pango ATTR TYPE :(pango attr property / tag property)
    pango_translation_properties = {
        pango.ATTR_SIZE: 'size',
        pango.ATTR_WEIGHT: 'weight',
        pango.ATTR_UNDERLINE: 'underline',
        pango.ATTR_STRETCH: 'stretch',
        pango.ATTR_VARIANT: 'variant',
        pango.ATTR_STYLE: 'style',
        pango.ATTR_SCALE: 'scale',
        pango.ATTR_FAMILY: 'family',
        pango.ATTR_STRIKETHROUGH: 'strikethrough',
        pango.ATTR_RISE: 'rise'}
    pango_type_table = {
        pango.ATTR_SIZE: pango.AttrInt,
        pango.ATTR_WEIGHT: pango.AttrInt,
        pango.ATTR_UNDERLINE: pango.AttrInt,
        pango.ATTR_STRETCH: pango.AttrInt,
        pango.ATTR_VARIANT: pango.AttrInt,
        pango.ATTR_STYLE: pango.AttrInt,
        pango.ATTR_SCALE: pango.AttrFloat,
        pango.ATTR_FAMILY: pango.AttrString,
        pango.ATTR_FONT_DESC: pango.AttrFontDesc,
        pango.ATTR_STRIKETHROUGH: pango.AttrInt,
        pango.ATTR_BACKGROUND: pango.AttrColor,
        pango.ATTR_FOREGROUND: pango.AttrColor,
        pango.ATTR_RISE: pango.AttrInt}

    attval_to_markup = {
        'underline': {pango.UNDERLINE_SINGLE: 'single',
                      pango.UNDERLINE_DOUBLE: 'double',
                      pango.UNDERLINE_LOW: 'low',
                      pango.UNDERLINE_NONE: 'none'
                      },
        'stretch': {pango.STRETCH_ULTRA_EXPANDED: 'ultraexpanded',
                    pango.STRETCH_EXPANDED: 'expanded',
                    pango.STRETCH_EXTRA_EXPANDED: 'extraexpanded',
                    pango.STRETCH_EXTRA_CONDENSED: 'extracondensed',
                    pango.STRETCH_ULTRA_CONDENSED: 'ultracondensed',
                    pango.STRETCH_CONDENSED: 'condensed',
                    pango.STRETCH_NORMAL: 'normal',
                    },
        'variant': {pango.VARIANT_NORMAL: 'normal',
                    pango.VARIANT_SMALL_CAPS: 'smallcaps',
                    },
        'style': {pango.STYLE_NORMAL: 'normal',
                  pango.STYLE_OBLIQUE: 'oblique',
                  pango.STYLE_ITALIC: 'italic',
                  },
        'stikethrough': {1: 'true',
                         True: 'true',
                         0: 'false',
                         False: 'false'
                         }}

    def __init__(self):
        self.tagdict = {}
        self.tags = {}
        gtk.TextBuffer.__init__(self)

    def set_text(self, txt):
        gtk.TextBuffer.set_text(self, "")
        suc, self.parsed, self.txt, self.separator = pango.parse_markup(txt, -1, u'\x00')
        if not suc:
            oldtxt = txt
            txt = saxutils.escape(txt)
            self.warn("Marked text is not correct. Escape %s to %s", oldtxt, txt)
            suc, self.parsed, self.txt, self.separator = pango.parse_markup(txt, -1, u'\x00')
        self.attrIter = self.parsed.get_iterator()
        self.add_iter_to_buffer()
        while self.attrIter.next():
            self.add_iter_to_buffer()

    def add_iter_to_buffer(self):
        it_range = self.attrIter.range()
        font, lang, attrs = self.attrIter.get_font()
        tags = self.get_tags_from_attrs(font, lang, attrs)
        text = self.txt[it_range[0]:it_range[1]]
        if tags:
            self.insert_with_tags(self.get_end_iter(), text, *tags)
        else:
            self.insert_with_tags(self.get_end_iter(), text, *tags)

    def get_tags_from_attrs(self, font, lang, attrs):
        tags = []
        if font:
            fontattrs = self.fontdesc_to_attrs(font)
            fontdesc = font.to_string()
            if fontattrs:
                attrs.extend(fontattrs)
        if lang:
            if not lang in self.tags:
                tag = self.create_tag()
                tag.set_property('language', lang)
                self.tags[lang] = tag
            tags.append(self.tags[lang])
        if attrs:
            for a in attrs:
                #FIXME remove on pango fix
                type_ = a.klass.type
                klass = a.klass
                start_index = a.start_index
                end_index = a.end_index
                a.__class__ = self.pango_type_table[type_]
                a.type = type_
                a.start_index = start_index
                a.end_index = end_index
                a.klass = klass
                if a.type == pango.ATTR_FOREGROUND:
                    gdkcolor = self.pango_color_to_gdk(a.color)
                    key = 'foreground%s' % self.color_to_hex(gdkcolor)
                    if not key in self.tags:
                        self.tags[key] = self.create_tag()
                        self.tags[key].set_property('foreground-gdk', gdkcolor)
                        self.tagdict[self.tags[key]] = {}
                        self.tagdict[self.tags[key]]['foreground'] = "#%s" % self.color_to_hex(gdkcolor)
                    tags.append(self.tags[key])
                if a.type == pango.ATTR_BACKGROUND:
                    gdkcolor = self.pango_color_to_gdk(a.color)
                    key = 'background%s' % self.color_to_hex(gdkcolor)
                    if not key in self.tags:
                        self.tags[key] = self.create_tag()
                        self.tags[key].set_property('background-gdk', gdkcolor)
                        self.tagdict[self.tags[key]] = {}
                        self.tagdict[self.tags[key]]['background'] = "#%s" % self.color_to_hex(gdkcolor)
                    tags.append(self.tags[key])
                if a.type in self.pango_translation_properties:
                    prop = self.pango_translation_properties[a.type]
                    val = getattr(a, 'value')
                    #tag.set_property(prop, val)
                    mval = val
                    if prop in self.attval_to_markup:
                        if val in self.attval_to_markup[prop]:
                            mval = self.attval_to_markup[prop][val]
                    key = "%s%s" % (prop, val)
                    if not key in self.tags:
                        self.tags[key] = self.create_tag()
                        self.tags[key].set_property(prop, val)
                        self.tagdict[self.tags[key]] = {}
                        self.tagdict[self.tags[key]][prop] = mval
                    tags.append(self.tags[key])
        return tags

    def get_tags(self):
        tagdict = {}
        for pos in range(self.get_char_count()):
            iter = self.get_iter_at_offset(pos)
            for tag in iter.get_tags():
                if tag in tagdict:
                    if tagdict[tag][-1][1] == pos - 1:
                        tagdict[tag][-1] = (tagdict[tag][-1][0], pos)
                    else:
                        tagdict[tag].append((pos, pos))
                else:
                    tagdict[tag] = [(pos, pos)]
        return tagdict

    def split(self, interval, split_interval):
        #We want as less intervals as posible
        # interval represented []
        # split interval represented {}
        if interval == split_interval:
            return [interval]
        if interval[1] < split_interval[0] or split_interval[1] < interval[0]:
            return [interval]

        if interval[0] == split_interval[0]:
            if interval[1] < split_interval[1]:
                return [interval]
            else:
                return [(interval[0], split_interval[1]),
                        (split_interval[1] + 1, interval[1])]

        if interval[0] < split_interval[0]:
            if interval[1] == split_interval[1]:
                return [(interval[0], split_interval[0] - 1),
                         (split_interval[0], interval[1])]
            elif interval[1] < split_interval[1]:
                return [(interval[0], split_interval[0] - 1),
                         (split_interval[0], interval[1])]
            else:  # interval[1] > split_interval[1]
                return [(interval[0], split_interval[0] - 1),
                         (split_interval[0], split_interval[1]),
                         (split_interval[1] + 1, interval[1])]

        if interval[0] > split_interval[0]:
            if interval[1] == split_interval[1]:
                return [interval]
            elif interval[1] < split_interval[1]:
                return [interval]
            else:  # interval[1] > split_interval[1]
                return [(interval[0], split_interval[1]),
                        (split_interval[1] + 1, interval[1])]

    def split_overlap(self, tagdict):
        intervals = []
        for k, v in tagdict.items():
            #Split by exiting intervals
            tmpint = v
            for i in intervals:
                iterint = tmpint
                tmpint = []
                for st, e in iterint:
                    tmpint.extend(self.split((st, e), i))
            tagdict[k] = tmpint
            #Add new intervals
            intervals.extend(tmpint)
        return tagdict

    def get_text(self, start=None, end=None, include_hidden_chars=True):
        tagdict = self.get_tags()
        if not start:
            start = self.get_start_iter()
        if not end:
            end = self.get_end_iter()
        txt = unicode(gtk.TextBuffer.get_text(self, start, end, True))
        #Important step, split that no tags overlap
        tagdict = self.split_overlap(tagdict)
        cuts = {}
        for k, v in tagdict.items():
            stag, etag = self.tag_to_markup(k)
            for st, e in v:
                if st in cuts:
                    #add start tags second
                    cuts[st].append(stag)
                else:
                    cuts[st] = [stag]
                if e + 1 in cuts:
                    #add end tags first
                    cuts[e + 1] = [etag] + cuts[e + 1]
                else:
                    cuts[e + 1] = [etag]
        last_pos = 0
        outbuff = ""
        cut_indices = cuts.keys()
        cut_indices.sort()
        soffset = start.get_offset()
        eoffset = end.get_offset()
        cut_indices = filter(lambda i: eoffset >= i >= soffset, cut_indices)
        for c in cut_indices:
            if not last_pos == c:
                outbuff += saxutils.escape(txt[last_pos:c])
                last_pos = c
            for tag in cuts[c]:
                outbuff += tag
        outbuff += saxutils.escape(txt[last_pos:])
        return outbuff

    def tag_to_markup(self, tag):
        stag = "<span"
        for k, v in self.tagdict[tag].items():
            #family in gtk, face in pango mark language
            if k == "family":
                k = "face"
            stag += ' %s="%s"' % (k, v)
        stag += ">"
        return stag, "</span>"

    def fontdesc_to_attrs(self, font):
        nicks = font.get_set_fields().value_nicks
        attrs = []
        for n in nicks:
            if n in self.desc_to_attr_table:
                Attr, norm = self.desc_to_attr_table[n]
                # create an attribute with our current value
                attrs.append(Attr(getattr(font, 'get_%s' % n)()))
        return attrs

    def pango_color_to_gdk(self, pc):
        return gtk.gdk.Color(pc.red, pc.green, pc.blue)

    def color_to_hex(self, color):
        hexstring = ""
        for col in 'red', 'green', 'blue':
            hexfrag = hex(getattr(color, col) / (16 * 16)).split("x")[1]
            if len(hexfrag) < 2:
                hexfrag = "0" + hexfrag
            hexstring += hexfrag
        return hexstring

    def apply_font_and_attrs(self, font, attrs):
        tags = self.get_tags_from_attrs(font, None, attrs)
        for t in tags:
            self.apply_tag_to_selection(t)

    def remove_font_and_attrs(self, font, attrs):
        tags = self.get_tags_from_attrs(font, None, attrs)
        for t in tags:
            self.remove_tag_from_selection(t)

    def get_selection(self):
        bounds = self.get_selection_bounds()
        if not bounds:
            iter = self.get_iter_at_mark(self.insert_mark)
            if iter.inside_word():
                start_pos = iter.get_offset()
                iter.forward_word_end()
                word_end = iter.get_offset()
                iter.backward_word_start()
                word_start = iter.get_offset()
                iter.set_offset(start_pos)
                bounds = (self.get_iter_at_offset(word_start),
                          self.get_iter_at_offset(word_end + 1))
            else:
                bounds = (iter, self.get_iter_at_offset(iter.get_offset() + 1))
        return bounds

    def apply_tag_to_selection(self, tag):
        selection = self.get_selection()
        if selection:
            self.apply_tag(tag, *selection)
        self.emit("changed")

    def remove_tag_from_selection(self, tag):
        selection = self.get_selection()
        if selection:
            self.remove_tag(tag, *selection)
        self.emit("changed")

    def remove_all_tags(self):
        selection = self.get_selection()
        if selection:
            for t in self.tags.values():
                self.remove_tag(t, *selection)


class InteractivePangoBuffer(PangoBuffer):
    def __init__(self, normal_button=None, toggle_widget_alist=[]):
        """
        An interactive interface to allow marking up a gtk.TextBuffer.
        txt is initial text, with markup.  buf is the gtk.TextBuffer
        normal_button is a widget whose clicked signal will make us normal
        toggle_widget_alist is a list that looks like this:
            [(widget,(font, attr)), (widget2, (font, attr))]
         """
        PangoBuffer.__init__(self)
        if normal_button:
            normal_button.connect('clicked', lambda *args: self.remove_all_tags())
        self.tag_widgets = {}
        self.internal_toggle = False
        self.insert_mark = self.get_insert()
        self.connect('mark-set', self._mark_set_cb)
        self.connect('changed', self._changed_cb)
        for w, tup in toggle_widget_alist:
            self.setup_widget(w, *tup)

    def set_text(self, txt):
        self.disconnect_by_func(self._changed_cb)
        self.disconnect_by_func(self._mark_set_cb)
        PangoBuffer.set_text(self, txt)
        self.connect('changed', self._changed_cb)
        self.connect('mark-set', self._mark_set_cb)

    def setup_widget_from_pango(self, widg, markupstring):
        """setup widget from a pango markup string"""
        #font = pango.FontDescription(fontstring)
        suc, a, t, s = pango.parse_markup(markupstring, -1, u'\x00')
        ai = a.get_iterator()
        font, lang, attrs = ai.get_font()

        return self.setup_widget(widg, font, attrs)

    def setup_widget(self, widg, font, attr):
        tags = self.get_tags_from_attrs(font, None, attr)
        self.tag_widgets[tuple(tags)] = widg
        return widg.connect('toggled', self._toggle, tags)

    def _toggle(self, widget, tags):
        if self.internal_toggle:
            return
        if widget.get_active():
            for t in tags:
                self.apply_tag_to_selection(t)
        else:
            for t in tags:
                self.remove_tag_from_selection(t)

    def _mark_set_cb(self, buffer, iter, mark, *params):
        # Every time the cursor moves, update our widgets that reflect
        # the state of the text.
        if hasattr(self, '_in_mark_set') and self._in_mark_set:
            return
        self._in_mark_set = True
        if mark.get_name() == 'insert':
            for tags, widg in self.tag_widgets.items():
                active = True
                for t in tags:
                    if not iter.has_tag(t):
                        active = False
                self.internal_toggle = True
                widg.set_active(active)
                self.internal_toggle = False
        if hasattr(self, 'last_mark'):
            self.move_mark(self.last_mark, iter)
        else:
            self.last_mark = self.create_mark('last', iter, left_gravity=True)
        self._in_mark_set = False

    def _changed_cb(self, tb):
        if not hasattr(self, 'last_mark'):
            return
        # If our insertion point has a mark, we want to apply the tag
        # each time the user types...
        old_itr = self.get_iter_at_mark(self.last_mark)
        insert_itr = self.get_iter_at_mark(self.insert_mark)
        if old_itr != insert_itr:
            # Use the state of our widgets to determine what
            # properties to apply...
            for tags, w in self.tag_widgets.items():
                if w.get_active():
                    for t in tags:
                        self.apply_tag(t, old_itr, insert_itr)


class TitleEditor(Loggable):
    def __init__(self, instance, uimap):
        Loggable.__init__(self)
        Signallable.__init__(self)
        self.app = instance
        self.bt = {}
        self.settings = {}
        self.source = None
        self.created = False
        self.seeker = Seeker()

        #Drag attributes
        self._drag_events = []
        self._drag_connected = False
        self._tab_opened = False

        #Creat UI
        self._createUI()
        self.textbuffer = gtk.TextBuffer()
        self.pangobuffer = InteractivePangoBuffer()
        self.textarea.set_buffer(self.pangobuffer)

        #Conect updates
        self.textbuffer.connect("changed", self._updateSourceText)
        self.pangobuffer.connect("changed", self._updateSourceText)

        #Connect buttons
        self.pangobuffer.setup_widget_from_pango(self.bt["bold"], "<b>bold</b>")
        self.pangobuffer.setup_widget_from_pango(self.bt["italic"], "<i>italic</i>")
        self.pangobuffer.setup_widget_from_pango(self.bt["underline"], "<u>underline</u>")

    def _createUI(self):
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(get_ui_dir(), "titleeditor.ui"))
        builder.connect_signals(self)
        self.widget = builder.get_object("box1")
        self.editing_box = builder.get_object("editing_box")
        self.textarea = builder.get_object("textview1")
        self.markup_button = builder.get_object("markupToggle")
        self.info_bar_create = builder.get_object("infobar1")
        self.info_bar_insert = builder.get_object("infobar2")
        buttons = ["bold", "italic", "underline", "font", "font_fore_color", "font_back_color", "back_color"]

        for button in buttons:
            self.bt[button] = builder.get_object(button)
        settings = ["valignment", "halignment", "xpos", "ypos"]

        for setting in settings:
            self.settings[setting] = builder.get_object(setting)

        for n, en in {_("Custom"): "position",
                      _("Top"): "top",
                      _("Center"): "center",
                      _("Bottom"): "bottom",
                      _("Baseline"): "baseline"}.items():
            self.settings["valignment"].append(en, n)

        for n, en in {_("Custom"): "position",
                      _("Left"): "left",
                      _("Center"): "center",
                      _("Right"): "right"}.items():
            self.settings["halignment"].append(en, n)
        self.set_sensitive(False)

    def _focusedTextView(self, widget, notused_event):
        self.app.gui.timeline_ui.playhead_actions.set_sensitive(False)
        self.app.gui.timeline_ui.selection_actions.set_sensitive(False)

    def _unfocusedTextView(self, widget, notused_event):
        self.app.gui.timeline_ui.playhead_actions.set_sensitive(True)
        self.app.gui.timeline_ui.selection_actions.set_sensitive(True)

    def _backgroundColorButtonCb(self, widget):
        self.textarea.modify_base(self.textarea.get_state(), widget.get_color())
        color = widget.get_rgba()
        color_int = 0
        color_int += int(color.red * 255) * 256 ** 2
        color_int += int(color.green * 255) * 256 ** 1
        color_int += int(color.blue * 255) * 256 ** 0
        color_int += int(color.alpha * 255) * 256 ** 3
        self.debug("Setting title background color to %s", hex(color_int))
        self.source.set_background(color_int)

    def _frontTextColorButtonCb(self, widget):
        suc, a, t, s = pango.parse_markup("<span color='" + widget.get_color().to_string() + "'>color</span>", -1, u'\x00')
        ai = a.get_iterator()
        font, lang, attrs = ai.get_font()
        tags = self.pangobuffer.get_tags_from_attrs(None, None, attrs)
        self.pangobuffer.apply_tag_to_selection(tags[0])

    def _backTextColorButtonCb(self, widget):
        suc, a, t, s = pango.parse_markup("<span background='" + widget.get_color().to_string() + "'>color</span>", -1, u'\x00')
        ai = a.get_iterator()
        font, lang, attrs = ai.get_font()
        tags = self.pangobuffer.get_tags_from_attrs(None, None, attrs)
        self.pangobuffer.apply_tag_to_selection(tags[0])

    def _fontButtonCb(self, widget):
        font_desc = widget.get_font_name().split(" ")
        font_face = " ".join(font_desc[:-1])
        font_size = str(int(font_desc[-1]) * 1024)
        text = "<span face='" + font_face + "'><span size='" + font_size + "'>text</span></span>"
        suc, a, t, s = pango.parse_markup(text, -1, u'\x00')
        ai = a.get_iterator()
        font, lang, attrs = ai.get_font()
        tags = self.pangobuffer.get_tags_from_attrs(font, None, attrs)
        for tag in tags:
            self.pangobuffer.apply_tag_to_selection(tag)

    def _markupToggleCb(self, markup_button):
        self.textbuffer.disconnect_by_func(self._updateSourceText)
        self.pangobuffer.disconnect_by_func(self._updateSourceText)
        if markup_button.get_active():
            for name in self.bt:
                self.bt[name].set_sensitive(False)
            self.textbuffer.set_text(self.pangobuffer.get_text())
            self.textarea.set_buffer(self.textbuffer)
        else:
            for name in self.bt:
                self.bt[name].set_sensitive(True)
            self.pangobuffer.set_text(
                self.textbuffer.get_text(self.textbuffer.get_start_iter(),
                                         self.textbuffer.get_end_iter(), True))
            self.textarea.set_buffer(self.pangobuffer)
        self.textbuffer.connect("changed", self._updateSourceText)
        self.pangobuffer.connect("changed", self._updateSourceText)

    def set_sensitive(self, sensitive):
        if sensitive:
            self.info_bar_create.hide()
            self.editing_box.set_sensitive(True)
        else:
            self.info_bar_create.show()
            self.info_bar_insert.hide()
            self.editing_box.set_sensitive(False)

        self.preview(sensitive)

    def _updateFromSource(self):
        if self.source is not None:
            self.log("Title text set to %s", self.source.get_text())

            self.pangobuffer.set_text(self.source.get_text())
            self.textbuffer.set_text(self.source.get_text())
            self.settings['xpos'].set_value(self.source.get_xpos())
            self.settings['ypos'].set_value(self.source.get_ypos())
            self.settings['valignment'].set_active_id(self.source.get_valignment().value_name)
            self.settings['halignment'].set_active_id(self.source.get_halignment().value_name)
            if hasattr(self.source, "get_background"):
                self.bt["back_color"].set_visible(True)
                color = self.source.get_background()
                color = gtk.gdk.RGBA(color / 256 ** 2 % 256 / 255.,
                                     color / 256 ** 1 % 256 / 255.,
                                     color / 256 ** 0 % 256 / 255.,
                                     color / 256 ** 3 % 256 / 255.)
                self.bt["back_color"].set_rgba(color)
            else:
                self.bt["back_color"].set_visible(False)

    def _updateSourceText(self, updated_obj):
        if self.source is not None:
            if self.markup_button.get_active():
                text = self.textbuffer.get_text(self.textbuffer.get_start_iter(),
                                                self.textbuffer.get_end_iter(),
                                                True)
            else:
                text = self.pangobuffer.get_text()
            self.log("Source text updated to %s", text)
            self.source.set_text(text)
            self.preview()

    def _updateSource(self, updated_obj):
        if self.source is not None:
            for name, obj in self.settings.items():
                if obj == updated_obj:
                    if name == "valignment":
                        self.source.set_valignment(getattr(ges.TextVAlign, obj.get_active_id().upper()))
                        self.settings["ypos"].set_visible(obj.get_active_id() == "position")
                    elif name == "halignment":
                        self.source.set_halignment(getattr(ges.TextHAlign, obj.get_active_id().upper()))
                        self.settings["xpos"].set_visible(obj.get_active_id() == "position")
                    elif name == "xpos":
                        self.settings["halignment"].set_active_id("position")
                        self.source.set_xpos(obj.get_value())
                    elif name == "ypos":
                        self.settings["valignment"].set_active_id("position")
                        self.source.set_ypos(obj.get_value())
                    self.preview()
                    return

    def _reset(self):
        #TODO: reset not only text
        self.markup_button.set_active(False)
        self.pangobuffer.set_text("")
        self.textbuffer.set_text("")
        #Set right buffer
        self._markupToggleCb(self.markup_button)

    def set_source(self, source, created=False):
        self.debug("Source set to %s", str(source))
        self.source = None
        self._reset()
        self.created = created
        if source is None:
            self.set_sensitive(False)
        else:
            self.source = source
            self._updateFromSource()
            self.set_sensitive(True)

    def _createCb(self, unused_button):
        source = ges.TimelineTitleSource()
        source.set_text("")
        source.set_duration(long(gst.SECOND * 5))
        #Show insert infobar only if created new source
        self.info_bar_insert.show()
        self.set_source(source, True)

    def _insertEndCb(self, unused_button):
        self.info_bar_insert.hide()
        self.app.gui.timeline_ui.insertEnd([self.source])
        self.app.gui.timeline_ui.timeline.selection.setToObj(self.source, SELECT)
        #After insertion consider as not created
        self.created = False

    def preview(self, show=True):
        if not show:
            #Disconect
            if self._drag_connected:
                self.app.gui.viewer.target.disconnect_by_func(self.drag_notify_event)
                self.app.gui.viewer.target.disconnect_by_func(self.drag_press_event)
                self.app.gui.viewer.target.disconnect_by_func(self.drag_release_event)
                self._drag_connected = False
        elif self.source is not None and not self.created:
            self.seeker.flush()
            if not self._drag_connected and self._tab_opened:
                #If source is in timeline and title tab opened enable title drag
                self._drag_connected = True
                self.app.gui.viewer.target.connect("motion-notify-event", self.drag_notify_event)
                self.app.gui.viewer.target.connect("button-press-event", self.drag_press_event)
                self.app.gui.viewer.target.connect("button-release-event", self.drag_release_event)

    def drag_press_event(self, widget, event):
        if event.button == 1:
            self._drag_events = [(event.x, event.y)]
            #Update drag by drag event change, but not too often
            self.timeout = gobject.timeout_add(100, self.drag_update_event)
            #If drag goes out for 0.3 second, and do not come back, consider drag end
            self._drag_updated = True
            self.timeout = gobject.timeout_add(1000, self.drag_posible_end_event)

    def drag_posible_end_event(self):
        if self._drag_updated:
            #Updated during last timeout, wait more
            self._drag_updated = False
            return True
        else:
            #Not updated - posibly out of bounds, stop drag
            self.log("Drag timeout")
            self._drag_events = []
            return False

    def drag_update_event(self):
        if len(self._drag_events) > 0:
            st = self._drag_events[0]
            self._drag_events = [self._drag_events[-1]]
            e = self._drag_events[0]
            xdiff = e[0] - st[0]
            ydiff = e[1] - st[1]
            xdiff /= self.app.gui.viewer.target.get_allocated_width()
            ydiff /= self.app.gui.viewer.target.get_allocated_height()
            newxpos = self.settings["xpos"].get_value() + xdiff
            newypos = self.settings["ypos"].get_value() + ydiff
            self.settings["xpos"].set_value(newxpos)
            self.settings["ypos"].set_value(newypos)
            self.seeker.flush()
            return True
        else:
            return False

    def drag_notify_event(self, widget, event):
        if len(self._drag_events) > 0 and event.get_state() & gtk.gdk.BUTTON1_MASK:
            self._drag_updated = True
            self._drag_events.append((event.x, event.y))
            st = self._drag_events[0]
            e = self._drag_events[-1]

    def drag_release_event(self, widget, event):
        self._drag_events = []

    def tab_switched(self, unused_notebook, arg1, arg2):
        if arg2 == 2:
            self._tab_opened = True
            self.preview(True)
        else:
            self._tab_opened = False
            self.preview(False)
