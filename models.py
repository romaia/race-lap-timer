# -*- coding: utf-8 -*-
from storm.properties import Unicode, Int, DateTime
from storm.expr import And, Count
from storm.base import Storm
from storm.locals import Reference
from storm.store import AutoReload, Store
import datetime


def cached_property(f):
    """returns a cached property that is calculated by function f"""
    def get(self):
        try:
            return self._property_cache[f]
        except AttributeError:
            self._property_cache = {}
            x = self._property_cache[f] = f(self)
            return x
        except KeyError:
            x = self._property_cache[f] = f(self)
            return x

    return property(get)


class Race(Storm):
    __storm_table__ = 'race'

    id = Int(primary=True, default=AutoReload)
    name = Unicode()
    start_time = DateTime()
    end_time = DateTime()

    def start(self):
        now = datetime.datetime.now().replace(microsecond=0)
        self.start_time = now

    def get_categories(self):
        return Store.of(self).find(Category, race=self)

    @cached_property
    def start_hour(self):
        return self.start_time.time()

    @property
    def time_elapsed(self):
        if not self.start_time:
            return None
        delta = datetime.datetime.now() - self.start_time
        return datetime.timedelta(seconds=delta.seconds)


class Category(Storm):
    __storm_table__ = 'category'

    id = Int(primary=True, default=AutoReload)
    short_name = Unicode()
    name = Unicode()
    total_laps = Int()
    race_id = Int()
    race = Reference(race_id, 'Race.id')

    # FIXME: workarount for treeview sorting
    number = None
    total_time = None

    def update(self):
        self._complete_laps = None

    @property
    def is_last_lap(self):
        return self.completed_laps == (self.total_laps - 1)

    @property
    def completed_laps(self):
        if hasattr(self, '_complete_laps') and self._complete_laps is not None:
            return self._complete_laps

        store = Store.of(self)
        query = And(Racer.id == RacerLap.racer_id,
                    Racer.category_id == self.id)
        data = store.using(RacerLap, Racer).find((Count(1)), query)
        data = data.group_by(Racer.category_id, Racer.id)
        self._complete_laps = max(list(data) or [0])
        return self._complete_laps


class Racer(Storm):
    __storm_table__ = 'racer'

    id = Int(primary=True)
    number = Int()
    name = Unicode()
    category_id = Int()
    category = Reference(category_id, 'Category.id')

    race_id = Int()
    race = Reference(race_id, 'Race.id')

    def update(self):
        self._complete_laps = None
        self._last_lap = -1

    @property
    def last_lap(self):
        if hasattr(self, '_last_lap') and self._last_lap != -1:
            return self._last_lap

        store = Store.of(self)
        query = (RacerLap.racer_id == self.id)
        self._last_lap = store.find(RacerLap, query).order_by(RacerLap.event_time).last()
        return self._last_lap

    @property
    def is_finished(self):
        last_lap = self.last_lap
        if last_lap is None:
            return False
        return last_lap.remaining_laps == 0

    @property
    def completed_laps(self):
        if hasattr(self, '_complete_laps') and self._complete_laps is not None:
            return self._complete_laps

        self._complete_laps = self.get_laps().count()
        return self._complete_laps

    @property
    def total_time(self):
        last = self.last_lap
        if not last:
            return None
        delta = last.event_time - self.race.start_time
        return str(datetime.timedelta(seconds=delta.seconds))

    @cached_property
    def category_str(self):
        return self.category.name

    def add_lap(self):
        lap = RacerLap()
        lap.racer = self
        lap.race = self.race
        lap.event_time = datetime.datetime.now()
        Store.of(self).add(lap)
        return lap

    def get_laps(self, before=None):
        store = Store.of(self)
        query = (RacerLap.racer == self)
        if before is not None:
            query = And(query, RacerLap.event_time < before)
        return store.find(RacerLap, query).order_by(RacerLap.event_time)


class RacerLap(Storm):
    __storm_table__ = 'racer_lap'

    id = Int(primary=True, default=AutoReload)
    event_time = DateTime()
    race_id = Int()
    race = Reference(race_id, 'Race.id')
    racer_id = Int()
    racer = Reference(racer_id, 'Racer.id')

    @property
    def previous_lap(self):
        laps = self.racer.get_laps(before=self.event_time)
        return laps.last()

    @cached_property
    def number(self):
        return self.racer.number

    @cached_property
    def name(self):
        return self.racer.name

    @cached_property
    def category(self):
        return self.racer.category.short_name

    @cached_property
    def remaining_laps(self):
        return self.racer.category.total_laps - self.lap_number

    @cached_property
    def lap_time(self):
        previous = self.previous_lap
        if previous:
            delta = self.event_time - previous.event_time
        else:
            # This is the first lap. Calculate it using the race start.
            delta = self.event_time - self.race.start_time

        # Create a new timedelta without the microseconds
        return datetime.timedelta(seconds=delta.seconds)

    @cached_property
    def lap_number(self):
        laps = self.racer.get_laps(before=self.event_time)
        return laps.count() + 1
