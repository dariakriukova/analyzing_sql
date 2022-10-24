from decimal import Decimal
from typing import Sequence, Any, Optional

import click
from click import Context

from utils import flatten_options

IV_VOLTAGE_PRESETS = {
    'sm': '-10.0,-6.0,-0.01,1.0',
    'raptor': '-20.0,-10.0,-5.0,-0.01,1.0',
    'micronova': '-1.0,0.01,5.0,6.0,10.0,20.0',
}


class VoltagesOption(click.Option):
    def __init__(self,
                 param_decls: Sequence[str],
                 presets: dict[str, Sequence[Decimal]],
                 *args,
                 **kwargs: Any) -> None:
        self.presets = presets
        super().__init__(param_decls, *args, **kwargs)

    def type_cast_value(self, ctx, value):
        if value in self.presets:
            value = self.presets[value]

        value = flatten_options(ctx, self, [value])
        return list(map(Decimal, value))

    def get_help_record(self, ctx: Context) -> Optional[tuple[str, str]]:
        names, *_ = super().get_help_record(ctx)
        presets = '\n'.join(f"{name} ({voltages})" for name, voltages in self.presets.items())
        return names, self.help + f"\n\n\b\nPresets:\n{presets}."
