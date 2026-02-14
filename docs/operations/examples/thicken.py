from build123d import *
from tcv_screenshots import save_model

sphere = Sphere(5).face()
box = Box(2, 2, 12)
box.color = "blue"

result = ShapeList([thicken(f, .5) for f in sphere.intersect(box).faces()])
save_model([sphere, box, result], "thicken_face", {"alphas": [.5, .2], "reset_camera": "dimetric"})
