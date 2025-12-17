from flask import jsonify


def success_response(data=None, message="OK", status_code=200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    response = jsonify(payload)
    response.status_code = status_code
    return response


def error_response(message="Error", status_code=400, errors=None):
    payload = {"success": False, "message": message}
    if errors:
        payload["errors"] = errors
    response = jsonify(payload)
    response.status_code = status_code
    return response
