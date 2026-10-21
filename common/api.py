import json

from club.exceptions import ApiBadRequest


class API:
    @classmethod
    def parse_body(cls, request) -> dict:
        if request.content_type != "application/json":
            return request.POST.dict()

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError) as ex:
            raise ApiBadRequest(title="Invalid JSON body") from ex

        if not isinstance(data, dict):
            raise ApiBadRequest(title="JSON body must be an object")

        return data
