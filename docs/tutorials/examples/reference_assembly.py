import copy
from build123d import *

from tools.svg import write_svg, project_shapes
from tcv_screenshots import save_model

screw = import_step("M6-1x12-countersunk-screw.step")
locs = HexLocations(6, 10, 10).local_locations

screw_references = [copy.copy(screw).locate(loc) for loc in locs]
reference_assembly = Compound(children=screw_references)
reference_assembly.color = Color("white")

# save_model(reference_assembly, "reference_assembly")
# write_svg("reference_assembly", project_shapes(reference_assembly, show_hidden=False))
# export_step(reference_assembly, "reference_assembly.step")
