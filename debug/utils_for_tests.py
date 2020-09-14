def todict(obj, include_class_attrs=False, convert_private=False, include_none_fields=True):
    """Convert object to dict"""
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = todict(v, include_class_attrs, convert_private)
        return data
    elif hasattr(obj, "_ast"):
        return todict(obj._ast(), convert_private=convert_private)
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [todict(v, include_class_attrs, convert_private) for v in obj]
    elif hasattr(obj, "__dict__"):
        if convert_private:
            instance_attributes = [(key, value) for key, value in obj.__dict__.items() if not callable(value)]
        else:
            instance_attributes = [(key, value) for key, value in obj.__dict__.items() if
                                   not callable(value) and not key.startswith('_')]

        if include_class_attrs and hasattr(obj, "__class__"):
            class_attributes = [(key, value) for key, value in obj.__class__.__dict__.items() if
                                (key[:2] != "__") and (not callable(value))]
        else:
            class_attributes = []

        items = instance_attributes
        items.extend(class_attributes)

        # if include_none_fields or value: for include or exclude none fields
        data = dict(
            [(key, todict(value, include_class_attrs, convert_private, include_none_fields)) for key, value in items if
             include_none_fields or (value is not None and value != [] and value != "")])

        return data
    else:
        return obj
