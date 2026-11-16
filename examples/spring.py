"""Create a helical compression spring with a swept circular profile."""

# [Code]
from build123d import BuildLine, BuildPart, BuildSketch, Circle, Helix, sweep

with BuildPart() as spring:
    with BuildLine() as spring_path:
        Helix(radius=2, pitch=1, height=10)
    with BuildSketch(spring_path.line ^ 0) as spring_profile:
        Circle(radius=0.3)
    sweep()
# [End]
