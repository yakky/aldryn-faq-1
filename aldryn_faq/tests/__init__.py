# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import random
import string

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase

from cms.models import Title
from cms.utils.i18n import get_language_list
from djangocms_helper.utils import create_user
from hvad.test_utils.context_managers import LanguageOverride

from aldryn_faq.models import Category, Question
User = get_user_model()


class TestUtilityMixin(object):

    def rand_str(prefix='', length=16, chars=string.ascii_letters):
        return prefix + ''.join(random.choice(chars) for _ in range(length))


class AldrynFaqTest(TestCase):
    data = {
        "category1": {
            "en": {"name": "Example", "slug": "example", },
            "de": {"name": "Beispiel", "slug": "beispiel", }
        },
        "category2": {
            # This should *not* have a EN translation
            "de": {"name": "Beispiel2", "slug": "beispiel2", }
        },
        "question1": {
            "en": {"title": "Test Question", "answer_text": "Test Answer", },
            "de": {"title": "Testfrage", "answer_text": "Test Antwort"},
        },
        "question2": {
            # This should *not* have a EN translation
            "de": {"title": "Testfrage2", "answer_text": "Test Antwort2"},
        },
    }

    @staticmethod
    def reload(object):
        """Simple convenience method for re-fetching an object from the ORM."""
        return object.__class__.objects.get(id=object.id)

    def mktranslation(self, obj, lang, **kwargs):
        """Simple method of adding a translation to an existing object."""
        obj.translate(lang)
        for k, v in kwargs.iteritems():
            setattr(obj, k, v)
        obj.save()

    def setUp(self):
        """Setup a prebuilt and translated Question with Category
        for testing."""
        with LanguageOverride("en"):
            self.category1 = Category(**self.data["category1"]["en"])
            self.category1.save()
            self.question1 = Question(**self.data["question1"]["en"])
            self.question1.category = self.category1
            self.question1.save()

        # Make a DE translation of the category
        self.mktranslation(self.category1, "de",
            **self.data["category1"]["de"])
        # Make a DE translation of the question
        self.mktranslation(self.question1, "de",
            **self.data["question1"]["de"])

        with LanguageOverride("de"):
            # Make a DE-only Category
            self.category2 = Category(**self.data["category2"]["de"])
            self.category2.save()

            # Make a DE-only Question
            self.question2 = Question(**self.data["question2"]["de"])
            self.question2.category = self.category2
            self.question2.save()


class CMSRequestBasedTest(TestCase):

    languages = get_language_list()

    @classmethod
    def setUpClass(cls):
        cls.request_factory = RequestFactory()
        cls.user = create_user('normal', 'normal@admin.com', 'normal')
        cls.site1 = Site.objects.get(pk=1)

    @classmethod
    def tearDownClass(cls):
        User.objects.all().delete()

    def get_or_create_page(self, base_title=None, languages=None):
        from cms.api import create_page, create_title
        if not base_title:
            # No title? Create one.
            base_title = self.rand_str(prefix="page", length=8)
        if not languages:
            # If no langs supplied, use'em all
            languages = self.languages
        # If there is already a page with this title, just return it.
        try:
            page_title = Title.objects.get(title=base_title)
            return page_title.page.get_draft_object()
        except:
            pass

        # No? Okay, create one.
        page = create_page(base_title, 'fullwidth.html', language=languages[0])
        # If there are multiple languages, create the translations
        if len(languages) > 1:
            for lang in languages[1:]:
                title_lang = "{0}-{1}".format(base_title, lang)
                create_title(language=lang, title=title_lang, page=page)
                page.publish(lang)
        return page.get_draft_object()

    def get_page_request(self, page, user, path=None, edit=False, lang_code='en'):
        from cms.middleware.toolbar import ToolbarMiddleware
        path = path or page and page.get_absolute_url()
        if edit:
            path += '?edit'
        request = RequestFactory().get(path)
        request.session = {}
        request.user = user
        request.LANGUAGE_CODE = lang_code
        if edit:
            request.GET = {'edit': None}
        else:
            request.GET = {'edit_off': None}
        request.current_page = page
        mid = ToolbarMiddleware()
        mid.process_request(request)
        return request
