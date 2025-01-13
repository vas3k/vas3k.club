import json


class API:
    @classmethod
    def parse_body(cls, request) -> dict:
        try:
            return json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return request.POST.to_dict()

    @classmethod
    def get_str(cls, request, key):
        data = cls.parse_body(request)
        return str(data.get(key)) if key in data else None
