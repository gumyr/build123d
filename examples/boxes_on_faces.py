import build123d as bd

# from cadquery import exporters

with bd.BuildPart() as bp:
    bd.Box(3, 3, 3)
    with bd.Workplanes(*bp.faces()):
        bd.Box(1, 2, 0.1, rotation=(0, 0, 45))

    # exporters.export(
    #     bp.part,
    #     "boxes_on_faces.svg",
    #     opt={
    #         "width": 250,
    #         "height": 250,
    #         "marginLeft": 30,
    #         "marginTop": 30,
    #         "showAxes": False,
    #         "projectionDir": (1, 1, 1),
    #         # "strokeWidth": 0.1,
    #         "showHidden": False,
    #     },
    # )

if "show_object" in locals():
    show_object(bp.part.wrapped, name="box on faces")
