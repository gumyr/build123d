def get_bb_coords(shape: Shape) -> Tuple[float, float, float, float, float, float]:
    bb = shape.BoundingBox()
    return (bb.xmin, bb.ymin, bb.zmin, bb.xmax, bb.ymax, bb.zmax)


def build_tree(shapes: Iterable[Shape]):
    import rtree.index

    p = rtree.index.Property(dimension=3)
    t = rtree.index.RtreeContainer(properties=p)
    for shape in shapes:
        t.insert(shape, get_bb_coords(shape))
    return t


def face_outside(f: Face, ff: Face) -> bool:
    """f exists outside of ff"""
    # TODO: shortcut True if bbox intersection is 1d and f.Area() > 0
    return f.cut(ff).Area() > 0


def new_faces(self: T) -> T:
    """Find faces not present in parent"""
    old_faces = self.parent.findSolid().Faces()
    old_set = set(old_faces)
    new = [f for f in self.findSolid().Faces() if f not in old_set]
    new_tree = build_tree(new)
    old_tree = build_tree(
        f for f in old_faces if any(new_tree.intersection(get_bb_coords(f)))
    )
    new = [
        f
        for f in new
        if all(face_outside(f, ff) for ff in old_tree.intersection(get_bb_coords(f)))
    ]
    return self.newObject(new)


cq.Workplane.new_faces = new_faces
