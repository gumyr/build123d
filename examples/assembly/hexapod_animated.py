import sys

sys.path.insert(0, "examples/assembly")

import numpy as np

from build123d import *
from ocp_vscode.animation import Animation
from ocp_vscode import show
from hexapod_parts import Base, Stand, UpperLeg, LowerLeg
from assembly import reference, Assembly

# %%


base = Base("base")
stand = Stand("stand")
upper_leg = UpperLeg("upper_leg")
lower_leg = LowerLeg("lower_leg")

legs = [
    Assembly(
        children=[
            reference(
                upper_leg,
                label="upper_leg",
                location=Pos(i * 200, j * 50, 0),
            ),
            Assembly(
                children=[
                    reference(
                        lower_leg,
                        label="lower_leg",
                        location=Pos(i * 200 + 80, j * 50, 0),
                    )
                ],
                label=f"{side}_{loc}_lower_leg",
            ),
        ],
        label=f"{side}_{loc}_leg",
    )
    for i, side in enumerate(["left", "right"])
    for j, loc in enumerate(["front", "middle", "back"])
]

hexapod = Assembly(
    children=[
        reference(base, label="bottom", color="grey", location=Pos(-100, -100, 0)),
        reference(base, label="top", color="lightgray", location=Pos(-100, 100, 0)),
        reference(stand, label="front_stand", color="skyblue", location=Pos(0, -60, 0)),
        reference(stand, label="back_stand", color="skyblue", location=Pos(0, -120, 0)),
    ]
    + legs,
    label="hexapod",
)

print(hexapod.show_topology())
show(hexapod, render_joints=True)

# %%

hexapod.assemble("/hexapod/back_stand", "j_bottom", "/hexapod/bottom", "j_back_stand")
hexapod.assemble("/hexapod/front_stand", "j_bottom", "/hexapod/bottom", "j_front_stand")
hexapod.assemble("/hexapod/top", "j_bottom", "/hexapod/bottom", "j_top")

for side in ["left", "right"]:
    for loc in ["front", "middle", "back"]:
        hexapod.assemble(
            f"/hexapod/{side}_{loc}_leg/upper_leg",
            "j_hinge",
            f"/hexapod/bottom",
            f"j_{side}_{loc}",
            angle=-90,
            animate=True,
        )
        hexapod.assemble(
            f"/hexapod/{side}_{loc}_leg/{side}_{loc}_lower_leg/lower_leg",
            "j_front",
            f"/hexapod/{side}_{loc}_leg/upper_leg",
            "j_knee_back" if side == "left" else "j_knee_front",
            angle=-105 if side == "left" else 105,
            animate=True,
        )

print(hexapod.show_topology())
show(hexapod, render_joints=False, debug=False)

# %%

#
# Animation
#


def time_range(end, count):
    return np.linspace(0, end, count + 1)


def vertical(count, end, offset):
    ints = [min(180, (90 + i * (360 // count)) % 360) for i in range(count)]
    heights = [round(20 * np.sin(np.deg2rad(x) - 15), 1) for x in ints]
    heights.append(heights[0])
    return time_range(end, count), heights[offset:] + heights[1 : offset + 1]


def horizontal(end, reverse):
    horizontal_angle = 25
    angle = horizontal_angle if reverse else -horizontal_angle
    return time_range(end, 4), [0, angle, 0, -angle, 0]


animation = Animation(hexapod)

for name in Base.hinges_holes.keys():
    times, values = horizontal(4, "middle" not in name)
    animation.add_track(f"/hexapod/{name}_leg", "rz", times, values)

    times, values = vertical(8, 4, 0 if "middle" in name else 4)
    animation.add_track(f"/hexapod/{name}_leg/{name}_lower_leg", "rz", times, values)

animation.animate(2)

# %%
