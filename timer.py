#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import datetime

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

from kiwi.ui.delegates import GladeDelegate, ProxyDelegate
from kiwi.ui.forms import TextField, IntegerField, ChoiceField
from kiwi.ui.objectlist import Column  # , ObjectList

from storm.database import create_database
from storm.store import Store

from models import Racer, RacerLap, Category, Race

# import sys
# from storm.tracer import debug
# debug(True, stream=sys.stdout)


CATEGORIES = {
    u'EM': u'Estreante Masculino',
    u'EF': u'Estreante Feminino',
    u'EJ': u'Estreante Sub18',
    u'PF': u'Pro Feminino',
    u'PJ': u'Pro Junior',
    u'P25': u'Pro Sub25',
    u'P35': u'Pro Sub35',
    u'P45': u'Pro Sub45',
    u'P55': u'Pro Sub55',
}

CATEGORIES_LAPS = {
    u'EM': 4,
    u'EF': 4,
    u'EJ': 6,
    u'PF': 6,
    u'PJ': 8,
    u'P25': 8,
    u'P35': 8,
    u'P45': 8,
    u'P55': 8,
}


class RacerEditor(ProxyDelegate):

    fields = dict(
        name=TextField('Name', proxy=True),
        number=IntegerField('Número', proxy=True),
        category=ChoiceField('Categoria', proxy=True),
    )


class Form(GladeDelegate):
    widgets = ['name', 'number', 'category']
    race_widgets = ['start_hour', 'time_elapsed']

    def __init__(self):
        GladeDelegate.__init__(self,
                               gladefile="interface.ui",
                               delete_handler=self.quit_if_last)
        self.proxy = None
        self.db = create_database("sqlite:laps.sqlite")
        self.store = Store(self.db)

        self.race = self._check_race()
        self.race_proxy = self.add_proxy(self.race, self.race_widgets)

        self._check_categories()

        self.setup_widgets()

    def _check_race(self):
        race = self.store.find(Race).one()
        if race:
            return race

        race = Race()
        race.name = u'First race ever'
        self.store.add(race)
        self.store.commit()
        return race

    def _check_categories(self):
        categories = self.race.get_categories()
        if not categories.is_empty():
            return

        for short, name in CATEGORIES.items():
            cat = Category()
            cat.race = self.race
            cat.short_name = short
            cat.name = name
            cat.total_laps = CATEGORIES_LAPS[short]
            self.store.add(cat)

        self.store.commit()

    def setup_widgets(self):
        self.racer_field.set_sensitive(False)
        if not self.race.start_time:
            self.lap_number.set_sensitive(False)
        else:
            self.start_button.set_sensitive(False)

        large = pango.FontDescription('Lucida Sans 32')
        self.lap_number.modify_font(large)
        self.time_elapsed.modify_font(large)
        self.start_hour.modify_font(large)

        self.hpaned1.set_position(550)

        # Categores
        options = sorted([(c.name, c) for c in self.race.get_categories()])
        self.category.prefill(options)

        # Lists
        self.racers.set_columns([
            Column('name', title="Nome", data_type=str, sorted=True),
            Column('number', title='Número', data_type=int),
            Column('completed_laps', title='Voltas', data_type=int),
            Column('total_time', title='Tempo', data_type=str),
            # Column('category_str', title="Categoria", data_type=str)
        ])

        self.categories.set_columns([
            Column('short_name', title="Cat", data_type=str, sorted=True),
            Column('name', title="Category", data_type=str, expand=True),
            Column('completed_laps', title="Comp", data_type=int),
            Column('total_laps', title="Total", data_type=int)])

        self.log.set_columns([Column('id', data_type=int, visible=False),
                              Column('number', title="#", data_type=int),
                              Column('name', title="Nome", expand=True, data_type=str),
                              Column('event_time', title="Hora", data_type=datetime.time),
                              Column('lap_time', title="Tempo Volta", data_type=str),
                              Column('lap_number', title="Volta N", data_type=int),

                              Column('category', title="Cat", data_type=str),
                              Column('remaining_laps', title="Falta", data_type=int),
                              ])

        for category in self.race.get_categories():
            self.racers.append(None, category)
        for racer in self.store.find(Racer):
            self.racers.append(racer.category, racer)
            self.racers.expand(racer.category)

        self.log.extend(self.store.find(RacerLap))
        self.categories.extend(self.store.find(Category))

        # timer
        gobject.timeout_add(1000, self._update_timer)

        # Always show bottom of the log list.
        self.log.get_treeview().connect('size-allocate', self._treeview_changed)

        # Show finishing categories in bold
        self.categories.set_cell_data_func(self._on_categories__cell_data_func)
        self.log.set_cell_data_func(self._on_log__cell_data_func)
        self.racers.set_cell_data_func(self._on_racers__cell_data_func)

    def _on_categories__cell_data_func(self, column, renderer, category, text):
        if not isinstance(renderer, gtk.CellRendererText):
            return text

        completed_laps = category.completed_laps

        last_lap = completed_laps == (category.total_laps - 1)
        finished = completed_laps == category.total_laps

        renderer.set_property('weight-set', last_lap or finished)
        renderer.set_property('background-set', last_lap or finished)

        if last_lap or finished:
            renderer.set_property('weight', pango.WEIGHT_BOLD)

        if last_lap:
            renderer.set_property('background', 'yellow')
        elif finished:
            renderer.set_property('background', 'green')

        return text

    def _on_log__cell_data_func(self, column, renderer, racer_lap, text):
        if not isinstance(renderer, gtk.CellRendererText):
            return text

        remaining_laps = racer_lap.remaining_laps
        last_lap = remaining_laps == 1
        finished = remaining_laps == 0

        renderer.set_property('weight-set', last_lap or finished)
        renderer.set_property('background-set', last_lap or finished)
        if last_lap or finished:
            renderer.set_property('weight', pango.WEIGHT_BOLD)

        if last_lap:
            renderer.set_property('background', 'yellow')
        elif finished:
            renderer.set_property('background', 'green')

        return text

    def _on_racers__cell_data_func(self, column, renderer, racer, text):
        if not isinstance(renderer, gtk.CellRendererText):
            return text

        renderer.set_property('weight-set', False)
        renderer.set_property('background-set', False)
        if not isinstance(racer, Racer):
            return text

        racer_lap = racer.last_lap
        if not racer_lap:
            return text

        remaining_laps = racer_lap.remaining_laps
        last_lap = remaining_laps == 1
        finished = remaining_laps == 0

        renderer.set_property('weight-set', last_lap or finished)
        renderer.set_property('background-set', last_lap or finished)
        if last_lap or finished:
            renderer.set_property('weight', pango.WEIGHT_BOLD)

        if last_lap:
            renderer.set_property('background', 'yellow')
        elif finished:
            renderer.set_property('background', 'green')

        return text

    def _treeview_changed(self, widget, event):
        adj = self.log.get_scrolled_window().get_vadjustment()
        adj.set_value(adj.upper - adj.page_size)

    def _update_timer(self):
        self.race_proxy.update('time_elapsed')
        return True

    #
    #   Public API
    #

    def add_lap(self, number):
        racer = self.store.find(Racer, number=number).one()
        if not racer:
            print 'recer not found', number
            return

        if racer.is_finished:
            print 'racer finished', number
            return

        print 'add_lap', number
        lap = racer.add_lap()
        self.log.append(lap)

        # We need to recalculate the number of laps
        racer.category.update()
        racer.update()

        # Update the categories list.
        self.categories.refresh(racer.category)
        self.store.flush()
        self.store._connection.commit()

    def edit_racer(self, racer):
        self._current_model = racer
        self.racer_field.set_sensitive(True)
        if not self.proxy:
            self.proxy = self.add_proxy(racer, self.widgets)
        self.proxy.set_model(racer)

    def save_racer(self):
        racer = self._current_model
        self.store.add(racer)
        if self._is_new:
            self.racers.append(racer.category, racer, select=True)

        self.proxy.set_model(None)
        self.racer_field.set_sensitive(False)
        self.racers.refresh()
        self.store.commit()

        self.racers.flush()
        self._current_model = None

    #
    # Callbacks
    #

    def on_start_button__clicked(self, button):
        if self.race.start_time:
            return

        self.race.start()
        self.race_proxy.update('start_hour')
        self.lap_number.set_sensitive(True)
        self.start_button.set_sensitive(False)
        self.store.commit()

    def on_lap_number__activate(self, widget):
        try:
            number = int(widget.get_text())
        except:
            return

        self.add_lap(number)
        widget.set_text('')

    def on_racers__row_activated(self, widget, row):
        self._is_new = False
        if isinstance(row, Racer):
            self.edit_racer(row)

    def on_new_button__clicked(self, button):
        self._is_new = True
        racer = Racer()
        racer.category = self.category.get_selected()
        racer.race = self.race

        self.edit_racer(racer)

    def on_save_button__clicked(self, button):
        self.save_racer()


if __name__ == "__main__":
    window = Form()
    window.show_all()
    gtk.main()
