"""Convert scene JSON into executable Manim Python code."""

from __future__ import annotations

import json
import textwrap
from typing import Any


EFFECT_MAP = {
    "write": "Write",
    "fade_in": "FadeIn",
    "draw": "Create",
    "indicate": "Indicate",
}


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _effect_play(effect: str, var: str, run_time: float = 1.0) -> str:
    anim = EFFECT_MAP.get(effect, "Write")
    if anim == "Indicate":
        return f"self.play({anim}({var}), run_time={run_time})"
    return f"self.play({anim}({var}), run_time={run_time})"


def generate_manim_code(project: dict[str, Any]) -> str:
    scenes: list[dict[str, Any]] = project.get("scenes", [])
    title = project.get("title", "Math Studio")

    lines: list[str] = [
        "from manim import *",
        "",
        "",
        "class GeneratedScene(Scene):",
        "    def construct(self):",
    ]

    if title:
        if all(ord(c) < 128 for c in title):
            lines.append(f'        header = Text("{_escape(title)}", font_size=40)')
        else:
            lines.append(
                f'        header = Text("{_escape(title)}", font="Noto Sans CJK KR", font_size=40)'
            )
        lines.append("        header.to_edge(UP)")
        lines.append("        self.play(FadeIn(header), run_time=0.8)")
        lines.append("        self.wait(0.5)")
        lines.append("        self.play(FadeOut(header), run_time=0.5)")

    for i, scene in enumerate(scenes):
        scene_type = scene.get("type", "equation")
        effect = scene.get("effect", "write")
        wait = float(scene.get("wait", 2))
        var = f"obj_{i}"

        lines.append("")
        lines.append(f"        # Scene {i + 1}: {scene_type}")

        if scene_type == "equation":
            latex = scene.get("latex", "x = 1")
            lines.append(f'        {var} = MathTex(r"{_escape(latex)}", font_size=48)')
            lines.append(f"        {var}.move_to(ORIGIN)")
            lines.append(f"        {_effect_play(effect, var)}")
            lines.append(f"        self.wait({wait})")
            lines.append(f"        self.play(FadeOut({var}), run_time=0.6)")

        elif scene_type == "graph":
            func = scene.get("function", "x**2")
            x_min, x_max = scene.get("x_range", [-3, 3])
            y_min, y_max = scene.get("y_range", [-2, 8])
            color = scene.get("color", "BLUE")

            lines.extend(
                [
                    f"        axes_{i} = Axes(",
                    f"            x_range=[{x_min}, {x_max}, 1],",
                    f"            y_range=[{y_min}, {y_max}, 1],",
                    "            x_length=8,",
                    "            y_length=5,",
                    "            axis_config={\"include_tip\": True},",
                    "        ).add_coordinates()",
                    f"        graph_{i} = axes_{i}.plot(lambda x: {func}, color={color})",
                    f"        {var} = VGroup(axes_{i}, graph_{i})",
                    f"        {var}.move_to(ORIGIN)",
                    f"        self.play(Create(axes_{i}), run_time=1.0)",
                    f"        {_effect_play(effect, f'graph_{i}')}",
                ]
            )

            highlight = scene.get("highlight")
            if highlight == "vertex" and "x**2" in func.replace(" ", ""):
                lines.extend(
                    [
                        f"        dot_{i} = Dot(axes_{i}.coords_to_point(2, -1), color=YELLOW)",
                        f"        self.play(FadeIn(dot_{i}), run_time=0.8)",
                    ]
                )

            lines.append(f"        self.wait({wait})")
            lines.append(f"        self.play(FadeOut({var}), run_time=0.6)")
            if highlight == "vertex":
                lines.append(f"        self.play(FadeOut(dot_{i}), run_time=0.4)")

        elif scene_type == "text":
            content = scene.get("content", "")
            safe = content.replace('"', '\\"')
            if all(ord(c) < 128 for c in content):
                lines.append(f'        {var} = Text("{safe}", font_size=36)')
            else:
                lines.append(
                    f'        {var} = Text("{safe}", font="Noto Sans CJK KR", font_size=36)'
                )
            lines.append(f"        {var}.move_to(ORIGIN)")
            lines.append(f"        {_effect_play(effect, var)}")
            lines.append(f"        self.wait({wait})")
            lines.append(f"        self.play(FadeOut({var}), run_time=0.6)")

        elif scene_type == "steps":
            items = scene.get("items", [])
            for j, item in enumerate(items):
                step_var = f"step_{i}_{j}"
                lines.append(f'        {step_var} = MathTex(r"{_escape(item)}", font_size=40)')
                lines.append(f"        {step_var}.to_edge(UP).shift(DOWN * {j * 0.8})")
                lines.append(f"        self.play(Write({step_var}), run_time=0.8)")
            lines.append(f"        self.wait({wait})")
            for j in range(len(items)):
                lines.append(f"        self.play(FadeOut(step_{i}_{j}), run_time=0.4)")

    lines.append("")
    return "\n".join(lines)


def default_project() -> dict[str, Any]:
    return {
        "title": "이차함수 그래프",
        "scenes": [
            {
                "type": "equation",
                "latex": "y = x^2 - 4x + 3",
                "effect": "write",
                "wait": 2,
            },
            {
                "type": "graph",
                "function": "x**2 - 4*x + 3",
                "x_range": [-1, 5],
                "y_range": [-2, 6],
                "effect": "draw",
                "highlight": "vertex",
                "wait": 3,
            },
            {
                "type": "text",
                "content": "꼭짓점 (2, -1)",
                "effect": "fade_in",
                "wait": 2,
            },
        ],
    }


if __name__ == "__main__":
    print(generate_manim_code(default_project()))
