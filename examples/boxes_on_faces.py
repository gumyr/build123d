import build123d as bd

with bd.BuildPart() as bp:
    bd.Box(3, 3, 3)
    with bd.Workplanes(*bp.faces()):
        bd.Box(1, 2, 0.1, rotation=(0, 0, 45))

if "show_object" in locals():
    show_object(bp.part, name="box on faces")
