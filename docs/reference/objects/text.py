from build123d import Text, Pos, Compound, TextAlign, Align, Location, RadiusArc
from tcv_screenshots import save_model


text = "The quick brown fox"
save_model(Text(text, 10), "text", {"reset_camera": "top"})
path = RadiusArc((-50, 0), (50, 0), 100)
save_model([path, Text(text, 10, path=path, position_on_path=.5, text_align=(TextAlign.CENTER, TextAlign.BOTTOM))], "path", {"reset_camera": "top"})
save_model([Pos(Y=10) * Text(text, 10, "singleline"), Text(text, 10, "singleline", single_line_width=1)], "outline", {"reset_camera": "top"})
save_model(Compound.make_text(text, 10, "singleline"), "singleline", {"reset_camera": "top"})

text = "The quick brown\nfox jumped over\nthe lazy dog."
save_model([Location(), Text(text, 2, text_align=(TextAlign.LEFT, TextAlign.TOPFIRSTLINE))], "text_align", {"reset_camera": "top"})
save_model([Location(), Text(text, 2, align=(Align.MIN, Align.MIN))], "align", {"reset_camera": "top"})

t = Text("The", 10, "Source Sans 3 Black")
save_model([(Pos(Y=10) * t).wires(), t], "missing_glyph", {"reset_camera": "top"})
