from web_fractal.filters import FilterBase, FilterField


class DeckFilter(FilterBase):
    id: FilterField[int]
    owner_id: FilterField[int]
    title: FilterField[str]
    is_public: FilterField[bool]
