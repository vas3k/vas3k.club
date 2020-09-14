from django.test import SimpleTestCase

from debug.utils_for_tests import todict


class TestToDictFunction(SimpleTestCase):
    def test_convert_instance_variables(self):
        class TestClass:
            def __init__(self, instance_attribute_variable=2):
                self.instance_attribute_variable = instance_attribute_variable

        json_obj = todict(TestClass(), convert_private=False, include_none_fields=True)
        self.assertEqual(json_obj, {'instance_attribute_variable': 2})

    def test_convert_class_attributes(self):
        class TestClass:
            class_attribute_variable = 1

            def __init__(self, instance_attribute_variable=2):
                self.instance_attribute_variable = instance_attribute_variable

        # convert_private=False
        json_obj = todict(TestClass(), convert_private=False, include_none_fields=True)
        self.assertEqual(json_obj, {'instance_attribute_variable': 2})

        # convert_private=True
        json_obj = todict(TestClass(), convert_private=True, include_none_fields=True)
        self.assertEqual(json_obj, {'instance_attribute_variable': 2})

        # include_class_attrs=True
        json_obj = todict(TestClass(), convert_private=True, include_none_fields=True, include_class_attrs=True)
        self.assertEqual(json_obj, {'class_attribute_variable': 1,
                                    'instance_attribute_variable': 2})

    def test_not_convert_callable_methods(self):
        class TestClass:
            class_attribute_variable = 1

            def __init__(self, instance_attribute_variable=2):
                self.instance_attribute_variable = instance_attribute_variable

            def method_a(self):
                pass

        json_obj = todict(TestClass(), convert_private=True, include_none_fields=True, include_class_attrs=True)
        self.assertNotIn("method_a", json_obj)
        self.assertEqual(json_obj, {'class_attribute_variable': 1, 'instance_attribute_variable': 2})

    def test_convert_private_attribute_flag(self):
        class TestClass:
            def __init__(self):
                self.public_variable = 1
                self._private_variable = 2

        # convert_private=True
        json_obj = todict(TestClass(), convert_private=True, include_none_fields=True)
        self.assertEqual(json_obj, {'_private_variable': 2, 'public_variable': 1})

        # convert_private=False
        json_obj = todict(TestClass(), convert_private=False, include_none_fields=True)
        self.assertEqual(json_obj, {'public_variable': 1})
        self.assertNotIn("method_a", json_obj)

    def test_convert_types(self):
        class TestClass:
            def __init__(self):
                self.variable_int = 1
                self.variable_string = "hello world"
                self.variable_list = [1, 2, 3]
                self.variable_dict = {'a': 1, 'b': 2}
                self.variable_tuple = (1, 2)
                self.variable_boolean = True

        json_obj = todict(TestClass(), convert_private=True, include_none_fields=True)
        self.assertEqual(json_obj, {'variable_boolean': True,
                                    'variable_dict': {'a': 1, 'b': 2},
                                    'variable_int': 1,
                                    'variable_list': [1, 2, 3],
                                    'variable_string': 'hello world',
                                    'variable_tuple': [1, 2]})

    def test_convert_inner_objects(self):
        class TestClassA:
            def __init__(self):
                self.var_dict = {'a': 1, 'b': 2}

        class TestClassB:
            def __init__(self, other_obj):
                self.obj_with_inner_obj = other_obj

        json_obj = todict(TestClassB(other_obj=TestClassA()), convert_private=True, include_none_fields=True)
        self.assertEqual(json_obj, {'obj_with_inner_obj': {'var_dict': {'a': 1, 'b': 2}}})

    def test_include_none_fields_flag(self):
        class TestClass:
            def __init__(self):
                self.var_int0 = 0
                self.var_int1 = 1
                self.var_string_empty = ""
                self.var_string = "hello world"
                self.var_list_empty = []
                self.var_list = [1, 2, 3]
                self.var_bool_false = False
                self.var_bool_true = True
                self.var_none = None

        # include_none_fields=True
        json_obj = todict(TestClass(), convert_private=False, include_none_fields=True)
        self.assertEqual(json_obj, {'var_bool_false': False,
                                    'var_bool_true': True,
                                    'var_int0': 0,
                                    'var_int1': 1,
                                    'var_list': [1, 2, 3],
                                    'var_list_empty': [],
                                    'var_none': None,
                                    'var_string': 'hello world',
                                    'var_string_empty': ''})

        # include_none_fields=False
        json_obj = todict(TestClass(), convert_private=False, include_none_fields=False)
        self.assertEqual(json_obj, {'var_bool_false': False,
                                    'var_bool_true': True,
                                    'var_int0': 0,
                                    'var_int1': 1,
                                    'var_list': [1, 2, 3],
                                    'var_string': 'hello world'})
