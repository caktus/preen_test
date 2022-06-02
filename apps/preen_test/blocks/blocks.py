from collections import OrderedDict

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList

from wagtail.core import blocks
from wagtail.core.blocks import PageChooserBlock
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock

from collections import deque
from html.parser import HTMLParser

from django.core.exceptions import ValidationError
from django.db.models import TextChoices
from django.forms.utils import ErrorList
from django.template.defaultfilters import pluralize

LETTERBOX_RATIO = Decimal(9 / 16)
RICHTEXT_SUBHEADING_FEATURES = ["bold", "italic", "ol", "ul", "link", "document_link"]

class ProperTagOrderParser(HTMLParser):
    """ An HTML parser that ensures tags are properly closed. """

    def __init__(self):
        super().__init__()
        self.tag_stack = deque()

    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        expected_tag = self.tag_stack.pop()
        if tag != expected_tag:
            line, offset = self.getpos()
            raise ValueError(
                'Unexpected closing tag on line {} ({} offset): got "{}", expected "{}"'.format(
                    line, offset, tag, expected_tag
                )
            )

    def close(self):
        if len(self.tag_stack) == 0:
            return
        raise ValueError(
            "Tag{} not closed: {}".format(pluralize(len(self.tag_stack), " was,s were"), ", ".join(self.tag_stack))
        )

def clean_html_field(fields, field_name):
    """ Validate a RawHTMLBlock field, ensuring that it is proper HTML. """
    try:
        parser = ProperTagOrderParser()
        parser.feed(fields.get(field_name))
        parser.close()
    except ValueError as error:
        field_details = {}
        field_details[field_name] = ErrorList([ValidationError(error)])
        raise ValidationError("Code validation error", params=field_details)
    except IndexError:
        field_details = {}
        field_details[field_name] = ErrorList([ValidationError("Encountered closed tag before it was opened")])
        raise ValidationError("Code validation error", params=field_details)


# # # # # # # # # # # # #
#    Abstract Blocks    #
# # # # # # # # # # # # #


class CopyBlock(blocks.StructBlock):
    """
    A shortcut for the common pattern of "Heading + Body" where:
    - `heading` is an H2 element
    - `body` is a RichTextBlock with somewhat limited features
    """

    heading = blocks.CharBlock()
    body = blocks.RichTextBlock(
        features=[
            "bold",
            "italic",
            "h2",
            "h3",
            "h4",
            "ol",
            "ul",
            "link",
            "document-link",
        ]
    )


class MultiLinkBlockBase(blocks.StructBlock):
    """
    The base block class for the link blocks that require various types of
    links.
    """

    def __init__(self, **kwargs):
        super().__init__()
        self._required = kwargs.get("required", False)

    internal_link = blocks.PageChooserBlock(required=False, help_text="Internal page")
    document_link = DocumentChooserBlock(required=False, help_text="Choose a document")
    external_link = blocks.URLBlock(required=False, help_text="External URL")

    @property
    def link_types(self):
        """
        Register link fields on subclasses for proper validation
        """
        return ["internal_link", "document_link", "external_link"]

    # Override base required property of wagtail Block, which currently always
    # returns False.
    @property
    def required(self):
        return self._required


class LinkBlockBase(MultiLinkBlockBase):
    display_text = blocks.CharBlock(
        required=False,
        help_text="Text to display for the link. If left blank, page or document title will be used",
    )

    def clean(self, value):
        """
        Ensure that:
            if display_text is provided or this block is "required", exactly one link is provided.
            if display_text is not provided, zero or one links are provided.
            if the provided link is external, display text is provided
        """
        value = super().clean(value)
        errors = {}
        error = None

        links_present = [l for l in self.link_types if value.get(l)]
        display_text = value.get("display_text")

        # If there is no display text, and this block is not marked required,
        # no links are needed. But one is needed if there is display_text,
        # or if this block is required.
        min_links = 1 if display_text or self.required else 0
        link_count = len(links_present)

        # If more than one link type was provided, deliver an error to
        # each one specified. Otherwise, if one is needed but none
        # provided, deliver an error to every single field where the
        # the link could have been provided.
        if link_count > 1:
            error = ValidationError("Only one link type may be specified.")
            errors = {key: ErrorList(error) for key in links_present}
        elif link_count < min_links:
            error = ValidationError("One link type must be provided.")
            errors = {key: ErrorList(error) for key in self.link_types}

        # If user selects "external_link", display_text must be provided
        if value.get("external_link") and not display_text:
            errors.update(
                {"display_text": ErrorList([ValidationError("Display text is required if using an external link")])}
            )

        if errors:
            raise ValidationError("Link block validation error", params=errors)
        return value

    class Meta:
        icon = "link"


class LinkWithoutTextBase(MultiLinkBlockBase):
    def clean(self, value):
        value = super().clean(value)
        errors = {}

        link_values = [k for k, v in value.items() if k in self.link_types and v]
        if len(link_values) != 1:
            for link_type in self.link_types:
                errors[link_type] = ErrorList([ValidationError("Must provide exactly one link type")])

        if errors:
            raise ValidationError("Link block validation error", params=errors)

        return value


class CTAButtonBlock(LinkBlockBase):
    styled_as_primary = blocks.BooleanBlock(required=False, initial=False, help_text="Styled to draw attention")

    class Meta:
        template = "blocks/cta_button_block.html"


class CTAButtonList(blocks.StreamBlock):
    cta_button = CTAButtonBlock(required=False, blank=True)

    class Meta:
        icon = "fa-ellipsis-h"
        template = "blocks/cta_button_list_block.html"


class ReorderableStructBlock(blocks.StructBlock):
    class Meta:
        field_order = None

    def _set_child_blocks_from_field_order(self):
        """
        If subclass defines self.meta.field_order, take whichever valid fields appear in that list
        and place them at the front of self.child_blocks OrderedDict. Any fields that do not appear
        in self.meta.field_order will be appended after in the order they are defined.
        """
        class_name = self.__class__.__name__
        if not self.meta.field_order:
            return

        for field in self.meta.field_order:
            if field not in self.child_blocks:
                raise ValueError(
                    f"Unknown field \"{field}\" found in {class_name}.meta.fields. Accepted values are {', '.join([k for k,v in self.child_blocks.items()])}"
                )

        # Create OrderedDict out of fields declared by self.meta.field_order
        reordered_child_blocks = OrderedDict((k, self.child_blocks[k]) for k in self.meta.field_order)

        # Every child_block...
        for name, block in self.child_blocks.items():
            # ... that has not been ordered by self.meta.field_order ...
            if name not in reordered_child_blocks:
                # ... append to OrderedDict in the order provided.
                reordered_child_blocks[name] = block

        # Override self.child_blocks with re-ordered OrderedDict
        self.child_blocks = reordered_child_blocks

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._set_child_blocks_from_field_order()


class VideoIframeBlockBase(blocks.StructBlock):
    """
    These videos are provided as iframes which handle all their own functionality.
    Because iframes are a black box, there is little to no validation we can perform
    on the code provided, except that it is valid html.
    """

    video_code = blocks.RawHTMLBlock(
        required=False,
        help_text=("Paste in your video iframe here"),
    )

    def clean(self, value):
        values = super().clean(value)
        return values


class SideBarLink(blocks.StructBlock):
    """
    Displays as a list of links with a descriptive title.
    """

    title = blocks.CharBlock(required=True, max_length=64)
    links = blocks.ListBlock(LinkBlockBase(required=True))

    class Meta:
        icon = "link"
        admin_text = "A series of links either internal or external"
        template = "blocks/sidebar_link_block.html"


class SimpleLinkWImageBlock(blocks.StructBlock):
    """
    A basic structure that defines a URL, Text, and an optional Image
    """

    display_text = blocks.CharBlock(required=True, max_length=128)
    link = blocks.URLBlock(required=False)
    image = ImageChooserBlock(required=False)

    class Meta:
        icon = "link"
        admin_text = "A simple link with optional image"
        template = "includes/simple_link_w_image.html"


class BaseContactFormChooser(blocks.StructBlock):
    """
    Concrete Blocks should implement a snippet chooser block with
    the concrete version, of the AbstractSimpleContact block, as the "contact_form"
    field.
    """

    class Meta:
        icon = "mail"
        template = "blocks/contact_form_block.html"


# # # # # # # #
#   Blocks    #
# # # # # # # #


class FullHeroBlock(VideoIframeBlockBase, ReorderableStructBlock):
    image = ImageChooserBlock(required=True)
    heading = blocks.CharBlock(required=True)
    heading_as_h1 = blocks.BooleanBlock(default=True, required=False)
    sub_heading = blocks.RichTextBlock(required=False, features=RICHTEXT_SUBHEADING_FEATURES)

    cta_buttons = CTAButtonList(required=False)

    class Meta:
        icon = "fa-picture-o"
        template = "blocks/full_hero_block.html"
        field_order = ["image", "video_code"]


class LinkTile(blocks.StructBlock):
    """
    A block with an image header a linkable title and description that renders as a card.
    """

    image = ImageChooserBlock(required=False, help_text="Optional image header for the tile")
    title = blocks.TextBlock(required=True)
    description = blocks.RichTextBlock(required=False, help_text="A short description to capture interest.")
    link = LinkWithoutTextBase(required=True)

    class Meta:
        icon = "fa-th-large"
        template = "blocks/link_tile_block.html"


class ColumnatedLinksBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, max_length=128, help_text="Optional header text for the block.")

    links = blocks.StreamBlock(
        [("simple_link", SimpleLinkWImageBlock(required=True))],
        label="A list of links to display in columns",
        required=True,
        min_num=2,
        icon="fa-link",
    )

    cta_button = CTAButtonBlock(required=False, help_text="Optional Call to Action")

    class Meta:
        icon = "fa-columns"
        admin_text = "A full-width block with links arranged in columns. Minimum of two links."
        template = "blocks/columnated_links_block.html"
        label = "Two columns of links"


class LocalChoices(TextChoices):
    ONE = '1', "One",
    TWO = '2', "Two",
    THREE = '3', "Three"


class ManualLinkTileBlock(blocks.StructBlock):

    image = ImageChooserBlock()
    document = DocumentChooserBlock()
    page = PageChooserBlock()
    text = blocks.RichTextBlock()
    choices = blocks.ChoiceBlock(choices=LocalChoices.choices)
    lists = blocks.ListBlock(child_block=blocks.RichTextBlock())
    tiles = blocks.StreamBlock([("tile", LinkTile()), ("fooblock", FullHeroBlock()), ("column_links", ColumnatedLinksBlock())], icon="fa-cards")

    class Meta:
        icon = "fa-th"
        template = "blocks/tile_grid_block.html"