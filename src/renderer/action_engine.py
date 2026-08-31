from __future__ import annotations

from typing import TYPE_CHECKING, Any

from manim import *

from src.config import ANSWER_COLOR, HIGHLIGHT_COLOR, KOREAN_FONT
from src.dsl.visual import VisualAction, VisualConfig
from src.renderer.expression import derivative_at, eval_expr, make_function, make_parametric_function
from src.renderer.graph_helpers import caption_bar, make_graph_axes

if TYPE_CHECKING:
    from src.scenes.hansu_scene import HansuSceneContext


COLOR_MAP: dict[str, ManimColor] = {
    "BLUE": BLUE,
    "TEAL": TEAL,
    "YELLOW": YELLOW,
    "RED": RED,
    "GREEN": GREEN,
    "ORANGE": ORANGE,
    "GRAY": GRAY,
    "WHITE": WHITE,
    "HIGHLIGHT": HIGHLIGHT_COLOR,
    "ANSWER": ANSWER_COLOR,
}


class ActionEngine:
    """Execute visual actions on a Manim scene (수학 한수 style)."""

    def __init__(self, ctx: HansuSceneContext) -> None:
        self.ctx = ctx
        self.scene = ctx.scene
        self.axes: Axes | None = None
        self.layer = VGroup()
        self.caption: Text | None = None

    def _color(self, name: str) -> ManimColor:
        return COLOR_MAP.get(name.upper(), BLUE)

    def ensure_axes(self, config: VisualConfig) -> Axes:
        if self.axes is None:
            xr = config.x_range
            yr = config.y_range
            self.axes = make_graph_axes(
                x_range=(xr[0], xr[1], max(1, (xr[1] - xr[0]) / 4)),
                y_range=(yr[0], yr[1], max(1, (yr[1] - yr[0]) / 4)),
            ).shift(DOWN * 0.15)
            self.scene.play(Create(self.axes), run_time=0.7)
            self.layer.add(self.axes)
        return self.axes

    def set_caption(self, text: str) -> None:
        new_cap = caption_bar(text)
        if self.caption is None:
            self.caption = new_cap
            self.scene.play(FadeIn(self.caption), run_time=0.35)
        else:
            self.scene.play(self.caption.animate.become(new_cap), run_time=0.35)
            self.caption = new_cap

    def execute(self, action: VisualAction, config: VisualConfig) -> None:
        handler = getattr(self, f"_action_{action.action}", None)
        if handler is None:
            return
        handler(action, config)
        if action.wait > 0:
            self.scene.wait(action.wait)

    def _action_caption(self, action: VisualAction, config: VisualConfig) -> None:
        if action.label:
            self.set_caption(action.label)

    def _action_plot(self, action: VisualAction, config: VisualConfig) -> None:
        axes = self.ensure_axes(config)
        assert action.expr is not None
        fn = make_function(action.expr)
        x0, x1 = (action.x_range or config.x_range)[:2]
        graph = axes.plot(fn, x_range=[x0, x1], color=self._color(action.color), stroke_width=3)
        label = None
        if action.label:
            label = MathTex(action.label, font_size=24, color=self._color(action.color)).next_to(
                axes, UP, buff=0.12
            )
        if label:
            self.scene.play(Create(graph), Write(label), run_time=1.0)
            self.layer.add(graph, label)
        else:
            self.scene.play(Create(graph), run_time=1.0)
            self.layer.add(graph)

    def _action_tangent_at(self, action: VisualAction, config: VisualConfig) -> None:
        axes = self.ensure_axes(config)
        assert action.expr is not None and action.x is not None
        x0 = action.x
        fn = make_function(action.expr)
        y0 = fn(x0)
        slope = derivative_at(action.expr, x0)
        tangent = axes.plot(
            lambda x: slope * (x - x0) + y0,
            x_range=[x0 - 1.0, x0 + 1.0],
            color=self._color(action.color or "YELLOW"),
            stroke_width=2.5,
        )
        point = Dot(axes.coords_to_point(x0, y0), color=YELLOW, radius=0.09)
        coord = MathTex(rf"({x0},\,{y0:.0f})", font_size=24, color=YELLOW).next_to(point, UR, buff=0.08)
        self.scene.play(FadeIn(point), Create(tangent), Write(coord), run_time=0.9)
        self.layer.add(point, tangent, coord)

    def _action_highlight_point(self, action: VisualAction, config: VisualConfig) -> None:
        axes = self.ensure_axes(config)
        assert action.x is not None
        x0 = action.x
        if action.y is not None:
            y0 = action.y
        elif action.expr is not None:
            y0 = eval_expr(action.expr, x0)
        else:
            y0 = 0.0
        dot = Dot(axes.coords_to_point(x0, y0), color=RED, radius=0.09)
        label = None
        if action.label:
            label = MathTex(action.label, font_size=22, color=RED).next_to(dot, UR, buff=0.08)
        anims: list[Any] = [GrowFromCenter(dot)]
        if label:
            anims.append(Write(label))
        self.scene.play(*anims, run_time=0.6)
        self.layer.add(dot)
        if label:
            self.layer.add(label)

    def _action_vertical_line(self, action: VisualAction, config: VisualConfig) -> None:
        axes = self.ensure_axes(config)
        assert action.x is not None
        x0 = action.x
        yr = config.y_range
        line = DashedLine(
            axes.coords_to_point(x0, yr[0]),
            axes.coords_to_point(x0, yr[1]),
            color=GRAY,
            stroke_width=1.5,
        ) if action.dashed else Line(
            axes.coords_to_point(x0, yr[0]),
            axes.coords_to_point(x0, yr[1]),
            color=GRAY,
            stroke_width=1.5,
        )
        label = MathTex(action.label or rf"x={x0:g}", font_size=24).next_to(
            axes.coords_to_point(x0, yr[0]), DOWN, buff=0.12
        )
        self.scene.play(Create(line), Write(label), run_time=0.6)
        self.layer.add(line, label)

    def _action_plot_piecewise(self, action: VisualAction, config: VisualConfig) -> None:
        axes = self.ensure_axes(config)
        assert config.expr and config.expr_right
        bp = config.breakpoint

        right = axes.plot(make_function(config.expr_right), x_range=[bp, config.x_range[1]], color=BLUE, stroke_width=3)
        self.scene.play(Create(right), run_time=0.7)
        self.layer.add(right)

        if action.param and action.from_value is not None and action.to_value is not None:
            tracker = ValueTracker(action.from_value)

            def left_graph() -> ParametricFunction | VMobject:
                fn = make_parametric_function(config.expr, action.param, tracker.get_value())
                return axes.plot(fn, x_range=[config.x_range[0], bp - 0.001], color=TEAL, stroke_width=3)

            left = always_redraw(left_graph)
            self.scene.add(left)
            self.layer.add(left)
            self.scene.play(tracker.animate.set_value(action.to_value), run_time=2.0, rate_func=smooth)
        else:
            left = axes.plot(make_function(config.expr), x_range=[config.x_range[0], bp - 0.001], color=TEAL, stroke_width=3)
            self.scene.play(Create(left), run_time=0.7)
            self.layer.add(left)

        self._action_vertical_line(
            VisualAction(action="vertical_line", x=bp, label=rf"x={bp:g}", dashed=True),
            config,
        )

    def _action_animate_param(self, action: VisualAction, config: VisualConfig) -> None:
        pass  # handled inside plot_piecewise

    def _action_show_equation(self, action: VisualAction, config: VisualConfig) -> None:
        assert action.label is not None
        eq = MathTex(action.label, font_size=36, color=self._color(action.color or "WHITE"))
        if eq.width > 5.5:
            eq.scale(5.5 / eq.width)
        eq.to_edge(RIGHT, buff=0.45).shift(DOWN * 0.3)
        box = SurroundingRectangle(eq, color=self._color(action.color or "HIGHLIGHT"), buff=0.12)
        self.scene.play(Write(eq), Create(box), run_time=0.8)
        self.layer.add(eq, box)

    def _action_fade_out(self, action: VisualAction, config: VisualConfig) -> None:
        if len(self.layer) > 0:
            self.scene.play(FadeOut(self.layer), run_time=0.45)
            self.layer = VGroup()
            self.axes = None

    def _action_clear(self, action: VisualAction, config: VisualConfig) -> None:
        self._action_fade_out(action, config)

    def _action_brace_y(self, action: VisualAction, config: VisualConfig) -> None:
        axes = self.ensure_axes(config)
        assert action.x is not None and action.from_value is not None and action.to_value is not None
        p0 = axes.coords_to_point(action.x, action.from_value)
        p1 = axes.coords_to_point(action.x, action.to_value)
        brace = BraceBetweenPoints(p0, p1, direction=RIGHT, color=RED)
        self.scene.play(GrowFromCenter(brace), run_time=0.5)
        self.layer.add(brace)
