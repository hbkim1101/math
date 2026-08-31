from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


VisualTemplate = Literal[
    "derivative_tangent",
    "piecewise_continuity",
    "equation_flow",
    "custom",
]

ActionType = Literal[
    "plot",
    "tangent_at",
    "highlight_point",
    "vertical_line",
    "animate_param",
    "show_equation",
    "fade_out",
    "clear",
    "plot_piecewise",
    "brace_y",
    "caption",
]


class VisualAction(BaseModel):
    action: ActionType
    expr: str | None = None
    color: str = "BLUE"
    x_range: list[float] | None = None
    x: float | None = None
    y: float | None = None
    label: str | None = None
    param: str | None = None
    from_value: float | None = Field(default=None, alias="from")
    to_value: float | None = Field(default=None, alias="to")
    pieces: list[dict[str, Any]] | None = None
    dashed: bool = False
    wait: float = 0.0

    model_config = {"populate_by_name": True}


class VisualConfig(BaseModel):
    template: VisualTemplate = "custom"
    expr: str | None = None
    expr_right: str | None = None
    breakpoint: float = 1.0
    param_name: str = "a"
    param_from: float = 0.0
    param_to: float = 3.0
    tangent_at: float | None = None
    x_range: list[float] = Field(default_factory=lambda: [-2.0, 2.0])
    y_range: list[float] = Field(default_factory=lambda: [-5.0, 15.0])
    actions: list[VisualAction] = Field(default_factory=list)
