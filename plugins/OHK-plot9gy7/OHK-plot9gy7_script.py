"""
Display condition for the Extend Expiration resource actions: the action is
shown only on a resource that has an expiration_date value. The blueprints in
this library do not set one; add an Expiration Date parameter to a blueprint to
make the action available on its resources.
"""


def should_display(resource, request=None):
    return bool(resource.get_value_for_custom_field("expiration_date"))
