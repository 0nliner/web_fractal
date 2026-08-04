from web_fractal.filters import FilterBase, FilterField


class UserFilter(FilterBase):
    id: FilterField[int]
    username: FilterField[str]
    email: FilterField[str]
    role: FilterField[str]
    is_active: FilterField[bool]
