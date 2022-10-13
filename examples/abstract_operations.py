import build123d as b


class MyRectangle(b.BaseSketchOperation):
    def __init__(self, width: float, height: float, rotation: float = 0, centered: tuple[bool, bool] = (True, True), mode: b.Mode = b.Mode.ADD):
        face = b.Face.makePlane(height, width)
        super().__init__(face, rotation, centered, mode)

class MyHole(b.BaseSketchOperation):
    def __init__(self, radius: float, rotation: float = 0, centered: tuple[bool, bool] = (True, True), mode: b.Mode = b.Mode.SUBTRACT):
        face = b.Face.makeFromWires(b.Wire.makeCircle(radius, (0, 0, 0), (0, 0, 1)))
        super().__init__(face, rotation, centered, mode)

with b.BuildSketch() as builder:
    MyRectangle(width=20, height=15, centered=(True, True), rotation=45)
    MyHole(radius=3)


if 'show_object' in locals():
    show_object(builder.sketch)
