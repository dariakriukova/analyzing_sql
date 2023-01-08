import typing as t
from collections.abc import Callable

from click import Choice, Parameter, Context

T = t.TypeVar('T')


class EntityChoice(Choice):
    def __init__(
            self, choices: t.Sequence[object], id_name_getter: Callable[[T], (int, str)] = None,
            multiple: bool = False) -> None:
        self.id_name_getter = id_name_getter or (lambda x: (x.id, x.name))
        self.entity_choices = choices
        self.multiple = multiple
        choice_ids = [str(self.id_name_getter(c)[0]) for c in choices]
        super().__init__(choice_ids, False)

    def get_metavar(self, param: "Parameter") -> str:
        descriptions = ["{:3} - {};".format(*self.id_name_getter(c)) for c in self.entity_choices]
        if self.multiple:
            descriptions.append("ALL - Select all above options;")
        return "\n    ".join([""] + descriptions)

    def convert(self, value: str, param: t.Optional[Parameter], ctx: t.Optional[Context]) -> t.Any:
        if self.multiple:
            return tuple(super(EntityChoice, self).convert(x, param, ctx) for x in value.split(','))
        else:
            return super(EntityChoice, self).convert(value, param, ctx)

    def __repr__(self) -> str:
        return f"EntityChoice({list(self.entity_choices)})"
