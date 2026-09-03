
from manim import *
import numpy as np

# Render:
#   manim -pqh calculus_visualization.py MeanValueCandidateScene
#
# Recommended for 16:9:
#   manim -p -r 1920,1080 calculus_visualization.py MeanValueCandidateScene


class MeanValueCandidateScene(Scene):
    def construct(self):
        # ---------- Background ----------
        self.camera.background_color = "#0A1630"

        # faint "chalkboard" math texture
        bg_texts = VGroup()
        snippets = [
            r"\int_a^b f(x)\,dx", r"\sum_{n=1}^{\infty}", r"\frac{a}{b}",
            r"\Delta x", r"\sin x", r"\cos x", r"f'(x)", r"x^2+y^2",
            r"\lim_{x\to a}", r"\sqrt{x}", r"\nabla f", r"\log x"
        ]
        rng = np.random.default_rng(4)
        for _ in range(34):
            tex = MathTex(rng.choice(snippets), color=BLUE_E)
            tex.set_opacity(0.09)
            tex.scale(rng.uniform(0.55, 1.05))
            tex.rotate(rng.uniform(-0.35, 0.35))
            tex.move_to([
                rng.uniform(-6.8, 6.8),
                rng.uniform(-3.7, 3.7),
                0
            ])
            bg_texts.add(tex)
        self.add(bg_texts)

        # ---------- Left equation ----------
        eq = MathTex(
            r"\frac{f(x)-f(1)}{x-1}",
            r"=",
            r"f'(g(x))",
            r"\quad (x\neq 1)",
            color=WHITE
        ).scale(1.08)
        eq.arrange(RIGHT, buff=0.20)
        eq.move_to(LEFT * 3.55 + UP * 1.15)

        self.play(Write(eq), run_time=1.2)

        # ---------- Main axes ----------
        axes = Axes(
            x_range=[0, 4.2, 1],
            y_range=[-0.6, 4.2, 1],
            x_length=3.5,
            y_length=3.05,
            tips=False,
            axis_config={"color": GREY_B, "stroke_width": 2},
        )
        axes.move_to(RIGHT * 3.25 + UP * 0.95)

        # Hide most tick labels; add custom labels
        x1_label = MathTex("1", color=YELLOW_E).scale(0.55)
        x1_label.next_to(axes.c2p(1, 0), DOWN, buff=0.08)

        x_label = MathTex("x", color=YELLOW_E).scale(0.65)
        x_label.next_to(axes.c2p(3.0, 0), DOWN, buff=0.08)

        # Function chosen only for visual similarity.
        def f(t):
            return 0.70 * (t - 1.15) * (t - 2.55) * (t - 3.35) + 2.85

        graph = axes.plot(
            f,
            x_range=[0.55, 3.65],
            color=RED_C,
            stroke_width=4
        )

        self.play(Create(axes), FadeIn(x1_label), Create(graph), run_time=1.1)

        # ---------- x tracker ----------
        tracker = ValueTracker(3.0)

        p1 = axes.c2p(1.0, f(1.0))

        moving_point = always_redraw(
            lambda: Dot(
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                radius=0.07,
                color=YELLOW
            )
        )
        fixed_point = Dot(p1, radius=0.07, color=YELLOW)

        secant = always_redraw(
            lambda: Line(
                p1,
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                color=GREEN_C,
                stroke_width=4
            ).scale(1.35)
        )

        x_dash = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), 0),
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                color=YELLOW_E,
                dash_length=0.08,
                dashed_ratio=0.55,
                stroke_width=2
            )
        )

        fixed_dash = DashedLine(
            axes.c2p(1.0, 0),
            p1,
            color=YELLOW_E,
            dash_length=0.08,
            dashed_ratio=0.55,
            stroke_width=2
        )

        self.play(
            FadeIn(fixed_point),
            FadeIn(moving_point),
            Create(fixed_dash),
            Create(x_dash),
            Create(secant),
            FadeIn(x_label),
            run_time=1.0
        )

        # ---------- Lower derivative graph ----------
        d_axes = Axes(
            x_range=[0, 4.2, 1],
            y_range=[-2.4, 2.4, 1],
            x_length=3.5,
            y_length=2.15,
            tips=False,
            axis_config={"color": GREY_B, "stroke_width": 2},
        )
        d_axes.move_to(RIGHT * 3.25 + DOWN * 2.15)

        def df(t):
            h = 1e-4
            return (f(t+h) - f(t-h)) / (2*h)

        deriv_graph = d_axes.plot(
            df,
            x_range=[0.55, 3.65],
            color=PURPLE_B,
            stroke_width=3
        )

        self.play(Create(d_axes), Create(deriv_graph), run_time=1.0)

        # secant slope m(x)
        def secant_slope(x):
            if abs(x - 1.0) < 1e-6:
                return df(1.0)
            return (f(x) - f(1.0)) / (x - 1.0)

        # Candidate g(x): visually two branches where f'(g)=secant slope.
        # We solve numerically on two intervals each frame.
        def candidates(x):
            target = secant_slope(x)
            grid = np.linspace(0.65, 3.55, 500)
            vals = np.array([df(t) - target for t in grid])
            roots = []
            for i in range(len(grid)-1):
                if vals[i] == 0 or vals[i] * vals[i+1] < 0:
                    a, b = grid[i], grid[i+1]
                    va, vb = vals[i], vals[i+1]
                    for _ in range(24):
                        m = (a+b)/2
                        vm = df(m) - target
                        if va * vm <= 0:
                            b, vb = m, vm
                        else:
                            a, va = m, vm
                    r = (a+b)/2
                    if not roots or abs(r - roots[-1]) > 0.03:
                        roots.append(r)
            if len(roots) == 0:
                return [1.0, 2.7]
            if len(roots) == 1:
                return [roots[0], roots[0]]
            return [roots[0], roots[-1]]

        # highlight candidate points on lower graph
        cand1 = always_redraw(
            lambda: Dot(
                d_axes.c2p(
                    candidates(tracker.get_value())[0],
                    df(candidates(tracker.get_value())[0])
                ),
                radius=0.065,
                color=YELLOW
            )
        )
        cand2 = always_redraw(
            lambda: Dot(
                d_axes.c2p(
                    candidates(tracker.get_value())[1],
                    df(candidates(tracker.get_value())[1])
                ),
                radius=0.065,
                color=YELLOW
            )
        )

        # dashed verticals linking main x to derivative candidates
        bridge1 = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                d_axes.c2p(
                    candidates(tracker.get_value())[0],
                    df(candidates(tracker.get_value())[0])
                ),
                color=TEAL_C,
                dash_length=0.08,
                dashed_ratio=0.55,
                stroke_width=2
            )
        )

        bridge2 = always_redraw(
            lambda: DashedLine(
                axes.c2p(tracker.get_value(), f(tracker.get_value())),
                d_axes.c2p(
                    candidates(tracker.get_value())[1],
                    df(candidates(tracker.get_value())[1])
                ),
                color=YELLOW_E,
                dash_length=0.08,
                dashed_ratio=0.55,
                stroke_width=2
            )
        )

        # tangent-ish cyan markers around the two candidate points
        def tangent_marker(root_index):
            def _mk():
                x = candidates(tracker.get_value())[root_index]
                y = df(x)
                p = d_axes.c2p(x, y)
                # small slanted line for visual annotation
                return Line(
                    p + LEFT * 0.32 + DOWN * 0.11,
                    p + RIGHT * 0.32 + UP * 0.11,
                    color=TEAL_A,
                    stroke_width=4
                )
            return always_redraw(_mk)

        marker1 = tangent_marker(0)
        marker2 = tangent_marker(1)

        # "g(x)의 후보" label and brace-ish lines
        label = Text("g(x)의 후보", font_size=30, color=TEAL_A)
        label.move_to(RIGHT * 5.15 + DOWN * 2.0)

        brace_top = Line(
            label.get_left() + LEFT*0.25 + UP*0.36,
            label.get_left() + LEFT*0.48 + UP*0.68,
            color=TEAL_A,
            stroke_width=3
        )
        brace_bottom = Line(
            label.get_left() + LEFT*0.25 + DOWN*0.36,
            label.get_left() + LEFT*0.48 + DOWN*0.68,
            color=TEAL_A,
            stroke_width=3
        )

        self.play(
            Create(bridge1),
            Create(bridge2),
            FadeIn(cand1),
            FadeIn(cand2),
            Create(marker1),
            Create(marker2),
            FadeIn(label),
            Create(brace_top),
            Create(brace_bottom),
            run_time=1.0
        )

        # ---------- Animation resembling the two screenshots ----------
        self.wait(0.5)

        # x starts relatively large and moves left toward 1:
        # candidates converge/move.
        self.play(
            tracker.animate.set_value(1.22),
            run_time=4.0,
            rate_func=smooth
        )

        self.wait(0.7)

        # then move x away again so candidate locations spread apart
        self.play(
            tracker.animate.set_value(3.0),
            run_time=4.0,
            rate_func=smooth
        )

        self.wait(1.0)
