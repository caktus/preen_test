from io import BytesIO

from django.core.files.images import ImageFile
from django.test import RequestFactory, TestCase

import factory
import PIL.Image
from faker import Faker
from wagtail.core.models import Collection, Page, Site
from wagtail.documents import get_document_model
from wagtail.images import get_image_model


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

