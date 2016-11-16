import os

from django import forms
from django.conf import settings
from django.template import EngineHandler, TemplateDoesNotExist
from django.template.backends.django import DjangoTemplates
from django.utils._os import upath
from django.utils.functional import cached_property

try:
    import jinja2
except ImportError:
    jinja2 = None

ROOT = upath(os.path.dirname(forms.__file__))


class StandaloneTemplateRenderer(object):
    """Render using only the built-in templates."""
    def get_template(self, template_name):
        return self.standalone_engine.get_template(template_name)

    def render(self, template_name, context, request=None):
        template = self.get_template(template_name)
        return template.render(context, request=request).strip()

    @cached_property
    def standalone_engine(self):
        if jinja2:
            from django.template.backends.jinja2 import Jinja2
            return Jinja2({
                'APP_DIRS': False,
                'DIRS': [os.path.join(ROOT, 'jinja2')],
                'NAME': 'djangoforms',
                'OPTIONS': {},
            })
        return DjangoTemplates({
            'APP_DIRS': False,
            'DIRS': [os.path.join(ROOT, 'templates')],
            'NAME': 'djangoforms',
            'OPTIONS': {},
        })


class TemplateRenderer(StandaloneTemplateRenderer):
    """Render first via TEMPLATES, then fall back to built-in templates."""
    def get_template(self, template_name):
        try:
            return get_template(template_name)
        except TemplateDoesNotExist as e:
            try:
                return super(TemplateRenderer, self).get_template(template_name)
            except TemplateDoesNotExist as e2:
                e.chain.append(e2)
            raise TemplateDoesNotExist(template_name, chain=e.chain)


def get_template(template_name, using=None):
    """
    A modified version of django.template.loader.get_template() that adds in
    the django.forms template directories if needed.
    """
    templates = settings.TEMPLATES
    for i, template in enumerate(templates):
        backend = template['BACKEND']
        jinja2_backend = backend == 'django.template.backends.jinja2.Jinja2'
        dtl_backend = backend == 'django.template.backends.django.DjangoTemplates'
        if template.get('APP_DIRS') and 'django.forms' not in settings.INSTALLED_APPS:
            if dtl_backend or jinja2_backend:
                templates[i].setdefault('DIRS', [])
                forms_template_dir = os.path.join(ROOT, 'templates' if dtl_backend else 'jinja2')
                if forms_template_dir not in templates[i]['DIRS']:
                    templates[i]['DIRS'].append(forms_template_dir)
                    break
    engines = EngineHandler(templates=templates)
    chain = []
    for engine in engines.all():
        try:
            return engine.get_template(template_name)
        except TemplateDoesNotExist as e:
            chain.append(e)
    raise TemplateDoesNotExist(template_name, chain=chain)
