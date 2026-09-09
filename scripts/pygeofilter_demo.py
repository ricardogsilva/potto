import shapely
from pygeofilter.parsers.cql2_text import parse
from pygeofilter.backends.native.evaluate import NativeEvaluator


items = [
    {"id": 1, "geom": shapely.Point(2, 3)},
    {"id": 2, "geom": shapely.Point(12, 13)},
]

bbox_filter_expression = parse("S_INTERSECTS(geom, BBOX(0, 0, 10, 10))")
envelope_filter_expression = parse("S_INTERSECTS(geom, ENVELOPE(0 10 0 10))")

evaluator = NativeEvaluator(
    function_map={"bbox": shapely.box},
    attribute_map={"id": "id", "geom": "geom"},
    use_getattr=False,
)

filter_bbox = evaluator.evaluate(bbox_filter_expression)
filter_envelope = evaluator.evaluate(envelope_filter_expression)

for i in items:
    print(filter_bbox(i), filter_envelope(i))
