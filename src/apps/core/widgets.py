import json
import logging

from django.conf import settings
from django.forms import widgets
from django.forms.widgets import MultiWidget, TextInput
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)


class LanguageFormsetWidget(MultiWidget):
    """
    A widget that renders JSONField language data as individual input fields
    for each language, making it work like a formset.
    """

    def __init__(self, languages=None, attrs=None):
        if languages is None:
            languages = list(dict(settings.LANGUAGES).keys())
        self.languages = languages

        # Create a TextInput widget for each language
        widgets_list = [
            TextInput(
                attrs={'placeholder': f'Text in {dict(settings.LANGUAGES).get(lang, lang.upper())}'}
            ) for lang in languages
        ]
        super().__init__(widgets_list, attrs)

    def render(self, name, value, attrs=None, renderer=None):
        """
        Override render to ensure format_output is called properly
        """
        if self.is_localized:
            for widget in self.widgets:
                widget.is_localized = self.is_localized
        # Render each widget
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs or {})
        id_ = final_attrs.get('id')
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except (IndexError, TypeError):
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id='%s_%s' % (id_, i))
            output.append(widget.render('%s_%s' % (name, i), widget_value, final_attrs, renderer))
        return mark_safe(self.format_output(output))

    def decompress(self, value):
        """
        Split the JSONField value into individual language values
        """
        if not value:
            return [""] * len(self.languages)

        if isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return [""] * len(self.languages)

        if isinstance(value, dict):
            return [value.get(lang, "") for lang in self.languages]

        return [""] * len(self.languages)

    def value_from_datadict(self, data, files, name):
        """
        Combine individual language values back into a JSON structure
        """
        values = {}
        for i, lang in enumerate(self.languages):
            widget_name = f"{name}_{i}"
            value = data.get(widget_name, "")
            values[lang] = value
        return values

    def format_output(self, rendered_widgets):
        """
        Format the output with labels for each language
        """
        output = ['<div class="language-formset">']
        for i, (lang, widget) in enumerate(zip(self.languages, rendered_widgets)):
            lang_display = dict(settings.LANGUAGES).get(lang, lang.upper())

            output.append(
                f'<div class="language-field" style="margin-bottom: 10px;">'
                f'<label style="display: block; font-weight: bold; margin-bottom: 5px;">{lang_display}:</label>'
                f'{widget}'
                f'</div>'
            )
        output.append('</div>')
        return mark_safe(''.join(output))


class PrettyJSONWidget(widgets.Textarea):

    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=2)
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split('\n')]
            self.attrs['rows'] = min(max(len(row_lengths) + 2, 10), 30)
            self.attrs['cols'] = min(max(max(row_lengths) + 2, 40), 120)
            return value
        except Exception as e:
            logger.warning("Error while formatting JSON: {}".format(e))
            return super(PrettyJSONWidget, self).format_value(value)
