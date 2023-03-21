from build123d import *

pipes = Rot(10, 20, 30) * Box(10, 10, 10)

for plane in [Plane(f) for f in pipes.faces()]:
    pipe = plane * Circle(4)
    pipes -= extrude(pipe, amount=-5)
    pipe = plane * Circle(4.5)
    pipe -= plane * Circle(4)

    last = pipes.edges()
    pipes += extrude(pipe, amount=10)
    pipes = fillet(pipes, pipes.edges() - last, radius=0.2)

if "show_object" in locals():
    show_object(pipes, name="intersecting pipes")
