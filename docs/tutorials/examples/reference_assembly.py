import copy
from build123d import *

screw = import_step("M6-1x12-countersunk-screw.step")
locs = HexLocations(6, 10, 10).local_locations

screw_references = [copy.copy(screw).locate(loc) for loc in locs]
reference_assembly = Compound(children=screw_references)
s = 100 / max(*reference_assembly.bounding_box().size)
svg = ExportSVG(scale=s)
svg.add_shape(reference_assembly)
svg.write("reference_assembly.svg")
# export_step(reference_assembly, "reference_assembly.step")
