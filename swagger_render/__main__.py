import yaml
import click
from jinja2 import Environment, PackageLoader
from .__version__ import __version__
from datetime import datetime

from .filters import add_filters
from .colors import colors


def resolve(base, val):
    """
    Makes a normal dictionary from a JSON Schema one
    """

    if type(val) == dict:
        data = {}
        for key, value in val.items():
            if key == "$ref" and type(value) is str:
                value = value.split("/")
                assert value.pop(0) == "#"
                pos = base
                while len(value) > 0:
                    pos = pos[value.pop(0)]
                data.update(resolve(base, resolve(base, pos)))
            if key == "allOf":
                return all_of(value)
            else:
                data[key] = resolve(base, value)
        return data
    if type(val) == list:
        return [resolve(base, item) for item in val]
    else:
        return val


def all_of(*items):
    """
    Merges the given items recursively

    >>> all_of("3", "2")
    '2'
    >>> sorted(all_of([1, 2], [3, 4]))
    [1, 2, 3, 4]
    >>> from pprint import pprint
    >>> pprint(all_of({"type": "object", "items": [1, 2], "foo": {"a": "bar"}}, \
                      {"type": "object", "items": [3], "foo": {"b": "baz"}}, \
                      {"items": [4]}))
    {'foo': {'a': 'bar', 'b': 'baz'}, 'items': [4, 3, 1, 2], 'type': 'object'}
    """

    items = list(items)

    if type(items[0]) == list:
        data = items.pop()
        while len(items) > 0:
            data += items.pop()
        return data
    if type(items[0]) in [str, int]:
        return items.pop()

    data = items.pop(0)

    for item in items:
        for key, value in item.items():
            if key in data:
                data[key] = all_of(data[key], value)
            else:
                data[key] = value

    return data


def merge_parameters(params1, params2):
    """
    Merges parameter lists, where uniqueness is defined by a combination of
    its name and location

    >>> from pprint import pprint
    >>> pprint(merge_parameters([{"name": "a", "location": "a"}, \
                                 {"name": "b", "location": "a"}], \
                                [{"name": "a", "location": "a", "data": "c"}, \
                                 {"name": "b", "location": "b"}]))
    [{'data': 'c', 'location': 'a', 'name': 'a'},
     {'location': 'a', 'name': 'b'},
     {'location': 'b', 'name': 'b'}]
    """

    data = {}
    for param in params1 + params2:
        data[param["name"] + "_" + param["location"]] = all_of(param, {})
    return sorted(list(data.values()), key=lambda x: x["name"] + x["location"])


def make_logical(data):
    for methods in data.paths.values():
        if "parameters" in methods:
            common_params = methods["parameters"]
            for method_name, method in methods.items():
                if method_name == "parameters":
                    continue
                params = method.get("parameters", [])
                method["parameters"] = merge_parameters(common_params, params)


def get_tags(data):
    """
    Gets all of the tags in the data

    >>> get_tags({ \
        "paths": { \
            "1": {"a": {"tags": ["c"]}, \
                  "b": {"tags": ["c"]}}, \
            "2": {"a": {"tags": ["b"]}, \
                  "d": {}}, \
            "3": {"c": {"tags": ["d", "e"]}} \
        } \
    })
    ['', 'b', 'c', 'd', 'e']
    """
    tags = set()
    for methods in data["paths"].values():
        for method in methods.values():
            tags |= set(method.get("tags", [""]))

    return sorted(list(tags))


@click.command()
@click.argument("swagger_path", type=click.Path(exists=True))
def main(swagger_path):
    env = Environment(loader=PackageLoader("swagger_render"))
    add_filters(env)

    with open(swagger_path, "r") as fp:
        data = yaml.load(fp.read())
    data = resolve(data, data)
    template = env.get_template("page.html")

    print(template.render(__version__=__version__,
                          __time__=datetime.utcnow(),
                          _colors=colors,
                          _tags=get_tags(data), **data))


if __name__ == "__main__":
    main()
