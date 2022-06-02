from io import BytesIO

from django.core.files.images import ImageFile
from django.test import RequestFactory, TestCase

import factory
import PIL.Image
from faker import Faker
from wagtail.core.models import Collection, Page, Site
from wagtail.documents import get_document_model
from wagtail.images import get_image_model

from bs4 import BeautifulSoup

from apps.gp_wagtail_block_library.tests.models import GPBLGeneralPage

Image = get_image_model()
Document = get_document_model()
faker = Faker()


def _get_collection():
    collection, created = Collection.objects.get_or_create(name="TestCollection", depth="001001001")
    return collection


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document


def get_test_image_file_png(filename="test.png", colour="white", size=(640, 480)):
    f = BytesIO()
    image = PIL.Image.new("RGB", size, colour)
    image.save(f, "PNG")
    return ImageFile(f, name=filename)


def get_test_image_file_jpeg(filename="test.jpg", colour="white", size=(640, 480)):
    f = BytesIO()
    image = PIL.Image.new("RGB", size, colour)
    image.save(f, "JPEG")
    return ImageFile(f, name=filename)


def get_test_document_file():
    doc = Document.objects.create(title="test document")
    return doc


def get_image_as_wagtail_image(this_title=None):
    if not this_title:
        this_title = faker.word()
    return Image.objects.create(
        title=f"Thumbnail of {this_title}", file=get_test_image_file_jpeg(), collection=_get_collection()
    )


class BasePageTest(TestCase):
    def setUp(self):
        self.home = GPBLGeneralPage(title="A Test Page")
        self.factory = RequestFactory()
        self.site = Site.objects.get(is_default_site=True)
        self.root = Page.get_first_root_node()

    def make_request(self):
        self.request = self.factory.get("/")
        self.response = self.home.serve(self.request)
        self.response.render()
        self.soup = BeautifulSoup(self.response.content, "html5lib")

    def get_search(self, query):
        self.response = self.client.get("/search/", {"query": query})
        self.soup = BeautifulSoup(self.response.content, "html5lib")

    def add_child_to_root(self, child=None):
        """
        Adds a child Page to the root node. If not specified make it the home page
        """
        if child:
            self.root.add_child(instance=child)
            return
        self.root.add_child(instance=self.home)

    def set_site_root_page(self, site_root=None):
        if site_root:
            self.site.root_page = site_root
        else:
            self.site.root_page = self.home
        self.site.save()

    def make_soup(self, html_to_soupify):
        """sets the soup to user defined html"""
        self.soup = BeautifulSoup(html_to_soupify, "html5lib")
