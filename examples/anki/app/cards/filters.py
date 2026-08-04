from datetime import datetime

from web_fractal.filters import FilterBase, FilterField


class CardFilter(FilterBase):
    id: FilterField[int]
    deck_id: FilterField[int]
    due_date: FilterField[datetime]
    interval: FilterField[int]
    repetitions: FilterField[int]
