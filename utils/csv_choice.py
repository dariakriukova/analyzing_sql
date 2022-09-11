import typing as t

from click import Choice, Parameter, Context


class CsvChoice(Choice):
    def convert(self, value: str, param: t.Optional[Parameter],
                ctx: t.Optional[Context]) -> t.Any:
        return tuple(super(CsvChoice, self).convert(x, param, ctx) for x in value.split(','))
