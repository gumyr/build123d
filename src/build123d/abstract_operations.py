from build123d import Face, Mode, BuildSketch, Location, LocationList, Compound, Vector


class BaseSketchOperation(Compound):
    def __init__(
        self,
        face: Face,
        rotation: float = 0,
        centered: tuple[bool, bool] = (True, True),
        mode: Mode = Mode.ADD,
    ):
        context: BuildSketch = BuildSketch._get_context()

        bounding_box = face.bounding_box()
        center_offset = Vector(
            0 if centered[0] else bounding_box.xlen / 2,
            0 if centered[1] else bounding_box.ylen / 2,
        )
        face = face.locate(
            Location((0, 0, 0), (0, 0, 1), rotation) * Location(center_offset)
        )

        new_faces = [
            face.moved(location)
            for location in LocationList._get_context().local_locations
        ]
        for face in new_faces:
            context._add_to_context(face, mode=mode)

        Compound.__init__(self, Compound.make_compound(new_faces).wrapped)
