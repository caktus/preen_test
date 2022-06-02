from faker import Faker
from wagtail.images.tests.utils import Image, get_test_image_file


class BaseGenerator:
    type = None

    def as_dict(self):
        return self.__dict__

    def as_block(self):
        if not self.type:
            raise NotImplementedError("Must provide a type.")
        return self.type, self.__dict__

    def as_stream_data(self):
        sd = []
        for k, v in self.as_dict().items():
            sd.append({"type": k, "value": v})
        return sd

    @staticmethod
    def short_text(chars=32):
        faker = Faker()
        return faker.text(max_nb_chars=chars)


class BaseBlockFactory:
    """
    Class to assist in the generation of a StreamValue consumable list of blocks.

    Params:
        generator: A class that provides an `as_stream_data` method
        block_class: The class of block you want the factory to provide.
        create: Number of block instances required.
    """

    def __init__(self, generator, block_class, create=3):
        self.generator = generator
        self.block_class = block_class
        self.create = create

    def _get_objects_raw(self):
        """Private method to create a list of serialized blocks based on the instantiated
        generator.

        Return: A list of dicts that declare the type of block and the values of the block.
        """
        objs = []
        for i in range(self.create):
            objs.append(
                {
                    "type": self.generator.type,
                    "value": self.generator().as_dict(),
                }
            )
        return objs

    def get_objects(self, lazy=False):
        objs = []
        raw_objects = self._get_objects_raw()
        if lazy:
            return raw_objects

        for obj in raw_objects:
            item = self.block_class().to_python(obj["value"])
            objs.append(
                (
                    self.generator.type,
                    item,
                )
            )
        return objs


class BasicHeroBlockGenerator(BaseGenerator):
    type = "hero"

    def __init__(self):
        faker = Faker()
        fake_title = faker.text(max_nb_chars=32)
        self.heading = faker.text(max_nb_chars=32)
        self.image = Image.objects.create(
            title=fake_title,
            file=get_test_image_file(filename=f"{fake_title}.png", colour="white"),
        )
        self.use_as_h1 = True


class AccordionGenerator(BaseGenerator):
    type = "accordion"

    def __init__(self, heading=None):
        self.heading = heading
        if not heading:
            self.heading = self.short_text()

        self.content = None
        self.embed = None

    def add_content(self, content=None):
        self.content = content
        if not content:
            self.content = self.short_text(chars=64)

    def add_embed(self, embed=None):
        self.embed = embed
        if not embed:
            self.embed = self.short_text()


class SidebarLinkGenerator(BaseGenerator):
    type = "sidebar_link"
    EXTERNAL = "external_link"
    INTERNAL = "internal_link"
    DOCUMENT = "document_link"

    def __init__(self, title=None, link_type=None):
        self.link_type = link_type
        if not title:
            self.title = self.short_text()
        if not self.link_type:
            self.link_type = self.EXTERNAL
        self.link_block = {
            "display_text": self.short_text(chars=64),
            "internal_link": None,
            "external_link": "",
            "document_link": None,
        }

    def add_link(self, link, display_text=None):
        if display_text:
            self.link_block["display_text"] = display_text
        self.link_block[self.link_type] = link


class CTAButtonGenerator(SidebarLinkGenerator):
    type = "cta_button"

    def __init__(self, primary=True):
        super().__init__()
        self.styled_as_primary = primary


class LinkBlockGenerator(BaseGenerator):
    type = "link_block"

    def __init__(self):
        self.display_text = self.short_text()
        self.internal_link = None
        self.document_link = None
        self.external_link = "www.example.com"


class LinkTileGenerator(BaseGenerator):
    type = "tile"

    def __init__(self):
        fake_title = self.short_text()
        self.title = self.short_text()
        self.link_block = LinkBlockGenerator().as_dict()
        image = Image.objects.create(
            title=fake_title,
            file=get_test_image_file(filename=f"{fake_title}.png", colour="white"),
        )
        self.image = image.pk
        self.description = self.short_text(chars=64)


class SimpleLinkWImageGenerator(BaseGenerator):
    type = "simple_link"

    def __init__(self, display_text=None, link=False, image=None):
        self.display_text = display_text
        if not display_text:
            self.display_text = self.short_text()
        if link:
            self.link = "www.example.com"


class ColumnatedLinksBlockGenerator(BaseGenerator):
    type = "columnated_links"

    def __init__(self, title=None, cta=None):
        if not title:
            self.title = self.short_text()
        if not cta:
            self.cta_button = CTAButtonGenerator().as_dict()


class CopyBlockGenerator(BaseGenerator):
    type = "copy"

    def __init__(self, heading="", body=""):
        self.heading = heading if heading else self.short_text()
        self.body = body if body else self.short_text()


class HtmlEmbedBlockGenerator(BaseGenerator):
    type = "html_embed"

    def __init__(self, code="", caption=""):
        super().__init__()
        self.code = code if code else "<div>Test html code</div>"
        self.caption = caption if caption else self.short_text()


class TwoColumnHtmlEmbedBlockGenerator(HtmlEmbedBlockGenerator):
    type = "two_column_html_embed"

    def __init__(self, copy=None, text_on_left=None):
        super().__init__()
        self.copy = copy if copy else CopyBlockGenerator().as_dict()
        self.text_on_left = text_on_left if text_on_left else True


class NewsletterSignupGenerator(BaseGenerator):
    type = "newsletter_signup"

    def __init__(self):
        fake_title = self.short_text()
        self.background_image = Image.objects.create(
            title=fake_title,
            file=get_test_image_file(filename=f"{fake_title}.png", colour="white"),
        )
        self.text = self.short_text()
