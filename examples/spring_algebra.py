"""Create a helical compression spring with a swept circular profile."""

# [Code]
from build123d import Circle, Helix, sweep

spring_path = Helix(radius=2, pitch=1, height=10)
spring_profile = (spring_path ^ 0) * Circle(radius=0.3)
spring = sweep(spring_profile, spring_path)
# [End]
