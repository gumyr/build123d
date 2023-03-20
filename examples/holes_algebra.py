from alg123d import *

thru_hole = Cylinder(radius=3, height=2)
thru_hole -= Bore(thru_hole, radius=1)

# Recessed counter bore hole (hole location = (0,0,0))
recessed_counter_bore = Cylinder(radius=3, height=2)
recessed_counter_bore -= CounterBore(
    recessed_counter_bore, radius=1, counter_bore_radius=1.5, counter_bore_depth=0.5
)

# Recessed counter sink hole (hole location = (0,0,0))
recessed_counter_sink = Cylinder(radius=3, height=2)
recessed_counter_sink -= CounterSink(
    recessed_counter_sink, radius=1, counter_sink_radius=1.5
)

# Flush counter sink hole (hole location = (0,0,2))
flush_counter_sink = Cylinder(radius=3, height=2)
plane = Plane(flush_counter_sink.faces().max())
flush_counter_sink -= plane * CounterSink(
    flush_counter_sink, radius=1, counter_sink_radius=1.5
)

if "show_object" in locals():
    show_object(thru_hole, name="though hole")
    show_object(Pos(10, 0) * recessed_counter_bore, name="recessed counter bore")
    show_object(Pos(0, 10) * recessed_counter_sink, name="recessed counter sink")
    show_object(Pos(10, 10) * flush_counter_sink, name="flush counter sink")
