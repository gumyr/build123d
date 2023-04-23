import sys

sys.path.insert(0, "examples/assembly")

from build123d import *
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
            reference(upper_leg, label=f"upper_leg"),
            reference(lower_leg, label=f"lower_leg"),
        ],
        label=f"{side}_{loc}_leg",
    )
    for side in ["left", "right"]
    for loc in ["front", "middle", "back"]
]


hexapod = Assembly(
    children=[
        reference(base, label="bottom", color="grey"),
        reference(base, label="top", color="lightgray"),
        reference(stand, label="front_stand", color="skyblue"),
        reference(stand, label="back_stand", color="skyblue"),
    ]
    + legs,
    label="hexapod",
)

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
            angle=180,
        )
        hexapod.assemble(
            f"/hexapod/{side}_{loc}_leg/lower_leg",
            "j_front",
            f"/hexapod/{side}_{loc}_leg/upper_leg",
            "j_knee_back" if side == "left" else "j_knee_front",
            angle=-75 if side == "left" else 75,
        )

print(hexapod.show_topology())
show(hexapod, render_joints=False, debug=False)

# %%
