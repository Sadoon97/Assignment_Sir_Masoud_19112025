"""
Unit Converter API (Flask)
File: lec2_flask.py

Endpoints:
- POST /convert  -> convert between units (JSON body: value, from_unit, to_unit)
- GET  /help     -> usage, allowed units, examples

Run:
    pip install flask
    python lec2_flask.py

Then open http://127.0.0.1:8000/help or test with Postman/curl.
"""
from flask import Flask, request, jsonify, make_response
from typing import Optional

app = Flask(__name__)

ALLOWED_UNITS = {
    "miles": "length",
    "mile": "length",
    "mi": "length",
    "kilometer": "length",
    "kilometers": "length",
    "km": "length",
    "kilometre": "length",
    "kilometres": "length",
    "pounds": "weight",
    "pound": "weight",
    "lb": "weight",
    "lbs": "weight",
    "kilogram": "weight",
    "kilograms": "weight",
    "kg": "weight",
    "celsius": "temperature",
    "c": "temperature",
    "fahrenheit": "temperature",
    "f": "temperature",
}

# Normalization map to canonical short keys used inside code
NORMALIZE = {
    # length
    "miles": "mi", "mile": "mi", "mi": "mi",
    "kilometer": "km", "kilometers": "km", "km": "km", "kilometre": "km", "kilometres": "km",
    # weight
    "pounds": "lb", "pound": "lb", "lbs": "lb", "lb": "lb",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    # temp
    "celsius": "c", "c": "c", "fahrenheit": "f", "f": "f",
}


def get_unit_type(unit: str) -> Optional[str]:
    if unit is None:
        return None
    return ALLOWED_UNITS.get(unit.lower())


def normalize(unit: str) -> Optional[str]:
    if unit is None:
        return None
    return NORMALIZE.get(unit.lower())


# Conversion helpers
def miles_to_km(mi: float) -> float:
    return mi * 1.609344


def km_to_miles(km: float) -> float:
    return km / 1.609344


def lb_to_kg(lb: float) -> float:
    return lb * 0.45359237


def kg_to_lb(kg: float) -> float:
    return kg / 0.45359237


def c_to_f(c: float) -> float:
    return (c * 9.0 / 5.0) + 32.0


def f_to_c(f: float) -> float:
    return (f - 32.0) * 5.0 / 9.0


def error_response(status: int, payload):
    """Helper to produce JSON error responses with desired status code."""
    return make_response(jsonify(payload), status)


@app.route("/convert", methods=["POST"])
def convert():
    # 1) Ensure JSON content
    if not request.is_json:
        return error_response(422, {"error": "Request must be JSON", "hint": "Set Content-Type: application/json"})

    body = request.get_json()

    # 2) Ensure required fields present
    missing = []
    for f in ("value", "from_unit", "to_unit"):
        if f not in body:
            missing.append(f)
    if missing:
        return error_response(422, {"error": "Missing fields", "missing": missing})

    # 3) Validate types
    value = body.get("value")
    from_unit_raw = body.get("from_unit")
    to_unit_raw = body.get("to_unit")

    # value must be numeric (int or float)
    try:
        value_num = float(value)
    except Exception:
        return error_response(422, {"error": "value must be a number", "provided": value})

    # from_unit/to_unit must be non-empty strings
    if not isinstance(from_unit_raw, str) or not from_unit_raw.strip():
        return error_response(422, {"error": "from_unit must be a non-empty string", "provided": from_unit_raw})
    if not isinstance(to_unit_raw, str) or not to_unit_raw.strip():
        return error_response(422, {"error": "to_unit must be a non-empty string", "provided": to_unit_raw})

    from_unit_raw = from_unit_raw.strip()
    to_unit_raw = to_unit_raw.strip()

    # 4) Validate unit existence and types
    from_type = get_unit_type(from_unit_raw)
    to_type = get_unit_type(to_unit_raw)

    if from_type is None:
        return error_response(422, {"error": "Unsupported from_unit", "provided": from_unit_raw, "allowed_units": sorted(list(ALLOWED_UNITS.keys()))})
    if to_type is None:
        return error_response(422, {"error": "Unsupported to_unit", "provided": to_unit_raw, "allowed_units": sorted(list(ALLOWED_UNITS.keys()))})

    # 5) Categories must match
    if from_type != to_type:
        return error_response(400, {"error": "Unsupported conversion types", "message": f"Cannot convert from {from_type} to {to_type}", "from_unit": from_unit_raw, "to_unit": to_unit_raw})

    # 6) Normalize units
    from_unit = normalize(from_unit_raw)
    to_unit = normalize(to_unit_raw)
    if from_unit is None or to_unit is None:
        return error_response(422, {"error": "Unit normalization failed", "from_unit": from_unit_raw, "to_unit": to_unit_raw})

    # 7) Disallow negative for length and weight
    if from_type in ("length", "weight") and value_num < 0:
        return error_response(400, {"error": "Negative value not allowed for selected unit type", "unit_type": from_type, "provided_value": value_num})

    # 8) Do conversion
    try:
        if from_type == "length":
            if from_unit == to_unit:
                converted = value_num
            elif from_unit == "mi" and to_unit == "km":
                converted = miles_to_km(value_num)
            elif from_unit == "km" and to_unit == "mi":
                converted = km_to_miles(value_num)
            else:
                return error_response(400, {"error": "Unsupported length conversion pair"})
        elif from_type == "weight":
            if from_unit == to_unit:
                converted = value_num
            elif from_unit == "lb" and to_unit == "kg":
                converted = lb_to_kg(value_num)
            elif from_unit == "kg" and to_unit == "lb":
                converted = kg_to_lb(value_num)
            else:
                return error_response(400, {"error": "Unsupported weight conversion pair"})
        elif from_type == "temperature":
            if from_unit == to_unit:
                converted = value_num
            elif from_unit == "c" and to_unit == "f":
                converted = c_to_f(value_num)
            elif from_unit == "f" and to_unit == "c":
                converted = f_to_c(value_num)
            else:
                return error_response(400, {"error": "Unsupported temperature conversion pair"})
        else:
            return error_response(500, {"error": "Unhandled unit type"})
    except Exception as e:
        return error_response(500, {"error": "Exception during conversion", "exception": str(e)})

    converted_rounded = round(converted, 6)

    resp = {
        "original_value": value_num,
        "original_unit": from_unit_raw,
        "converted_value": converted_rounded,
        "converted_unit": to_unit_raw,
        "conversion_type": from_type
    }
    return jsonify(resp)


@app.route("/help", methods=["GET"])
def help_endpoint():
    allowed = sorted(list(set(ALLOWED_UNITS.keys())))
    examples = [
        {"value": 5, "from_unit": "mi", "to_unit": "km"},
        {"value": 10, "from_unit": "kg", "to_unit": "lb"},
        {"value": -10, "from_unit": "celsius", "to_unit": "fahrenheit"}
    ]
    return jsonify({
        "description": "POST /convert with JSON body {value, from_unit, to_unit}",
        "allowed_units_examples": allowed[:30],
        "unit_categories": {
            "length": ["mi (miles)", "km (kilometers)"],
            "weight": ["lb (pounds)", "kg (kilograms)"],
            "temperature": ["c (celsius)", "f (fahrenheit)"]
        },
        "examples": examples,
        "edge_cases_handled": [
            "negative_values_for_length_or_weight -> rejected",
            "negative_temperature -> allowed",
            "unknown_units -> 422 with allowed units list",
            "unsupported_category_conversion -> 400"
        ],
        "notes": "Be careful in Postman to set Content-Type: application/json"
    })


if __name__ == "__main__":
    # debug=True gives automatic reload and stack traces during development.
    app.run(host="127.0.0.1", port=8000, debug=True)
