from jinja2 import evalcontextfilter
import markdown


@evalcontextfilter
def md(eval_ctx, value):
    return markdown.markdown(value)


@evalcontextfilter
def sane(eval_ctx, value):
    return ("_".join(value)).replace("/", "_").replace("{", "_").replace("}",
                                                                         "_")


@evalcontextfilter
def has_tag(eval_ctx, value):
    paths = value[0]
    tag = value[1]

    for path_name, methods in sorted(paths.items()):
        for method_name, method in sorted(methods.items()):
            if tag == "" and len(method.get("tags", [])) == 0:
                yield path_name, method_name, method
            elif len(tag) > 0 and tag in method.get("tags", []):
                yield path_name, method_name, method


@evalcontextfilter
def schema(eval_ctx, value):
    if "schema" in value:
        return value["schema"]
    if "type" in value:
        if value["type"] is "list":
            if "items" in value:
                return [schema(eval_ctx, value["items"])]
            return []
        return value["type"]
    return None


@evalcontextfilter
def render_object(eval_ctx, obj, offset=0):
    if obj is None:
        return ""
    if type(obj) is str:
        return obj

    if "type" in obj and obj["type"] == "array":
        if "items" in obj and obj["items"].get("type", "object") == "object":
            return "<div class=\"schema\">[{}]</div>".format(
                render_object(eval_ctx, obj["items"], offset + 1))
        return ""

    required = obj.get("required", [])
    properties = obj.get("properties", {})
    out = ""
    for key, value in sorted(properties.items()):
        out += "<div class=\"schema\">"
        out += "<span class=\"sKey\">{}</span>".format(key)
        out += " ("

        out += "<span class=\"sType\">{}".format(value["type"])

        if value["type"] == "array" and "items" in value:
            out += "[{}]".format(value["items"].get("type", "object"))

        out += "</span>"

        if key not in required:
            out += ", <span class=\"sOptional\">optional</span>"

        out += ")"

        if "description" in value:
            out += ": <span class=\"sDescription\">{}</span>".format(
                markdown.markdown(value["description"]))

        if value["type"] == "object" or "items" in value:
            out += render_object(eval_ctx, value, offset + 1)

        if "enum" in value:
            out += "<span class=\"enum\">[{}]</span>".format(
                " | ".join(value["enum"]))

        out += "</div>"

    return out


def add_filters(env):
    env.filters["md"] = md
    env.filters["sane"] = sane
    env.filters["schema"] = schema
    env.filters["render"] = render_object
    env.filters["has_tag"] = has_tag