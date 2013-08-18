# -*- coding: utf-8 -*-

import datetime

import pygtk
pygtk.require('2.0')
import gtk
import gobject
import pango

from kiwi.datatypes import ValidationError
from kiwi.ui.delegates import GladeDelegate, ProxyDelegate
from kiwi.ui.objectlist import Column
from kiwi.ui.dialogs import yesno

from storm.database import create_database
from storm.expr import And
from storm.store import Store

from models import Racer, RacerLap, Category, Race

def main():
    db = create_database("sqlite:laps.sqlite")
    store = Store(db)

    racers = store.find(Racer)
    print 'Categoria,Número,Nome,L1,L2,L3,L4,L5,L6,L7,L8,Total'
    for r in racers:
        data = [r.category.name, r.number, r.name]
        #print r.number, r.name
        for i, lap in enumerate(list(r.get_laps()), 1):
            assert i == lap.lap_number
            #print '  ', i, lap.lap_number, lap.lap_time, lap
            #data.append(str(lap.lap_time))
            data.append(lap.lap_time.seconds)

        data.extend([0] * (11 - len(data)))
        data.append(r.total_time)
        print ','.join(str(i) for i in data)


if __name__ == '__main__':
    main()
