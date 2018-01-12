from django.forms import Select, TextInput
from phonenumber_field.widgets import PhoneNumberPrefixWidget
from phonenumbers import COUNTRY_CODE_TO_REGION_CODE

from .validators import validate_possible_number


phone_prefixes = [
    ('+{}'.format(k), '+{}'.format(k)) for
    (k, v) in sorted(COUNTRY_CODE_TO_REGION_CODE.items())]


class PhonePrefixWidget(PhoneNumberPrefixWidget):
    """
    Overwrite widget to use choices with tuple in a simple form of "+XYZ: +XYZ"
    Workaround for an issue:
    https://github.com/stefanfoulis/django-phonenumber-field/issues/82
    """

    template_name = 'userprofile/snippets/phone-prefix-widget.html'

    def __init__(self, attrs=None):
        widgets = (Select(attrs=attrs, choices=phone_prefixes), TextInput())
        super(PhoneNumberPrefixWidget, self).__init__(widgets, attrs)

class DatalistTextWidget(Select):
    template_name = "userprofile/snippets/datalist.html"
    input_type = "text"

    def render(self, *args, **kwargs):
        return super(DatalistTextWidget, self).render(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super(DatalistTextWidget, self).get_context(name, value, attrs)
        context['widget']['type'] = self.input_type
        return context

    def format_value(self, value):
        value = super(DatalistTextWidget, self).format_value(value)
        value = value[0]
        if value:
            for choice in self.choices:
                if any(c.lower() == value.lower() for c in choice):
                    return choice[0]
            for choice in self.choices:
                if any(c.lower().startswith(value.lower()) for c in choice):
                    return choice[0]
            for choice in self.choices:
                if any(value.lower() in c.lower() for c in choice):
                    return choice[0]
        return value
