from collections import OrderedDict

from decimal import Decimal
from django.core.exceptions import ValidationError
from django.forms.utils import ErrorList

from wagtail.core import blocks
from wagtail.documents.blocks import DocumentChooserBlock
from wagtail.images.blocks import ImageChooserBlock


RICHTEXT_SUBHEADING_FEATURES = ["bold", "italic", "ol", "ul", "link", "document_link"]

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
        template = "gp_wagtail_block_library/blocks/cta_button_block.html"


class CTAButtonList(blocks.StreamBlock):
    cta_button = CTAButtonBlock(required=False, blank=True)

    class Meta:
        icon = "fa-ellipsis-h"
        template = "gp_wagtail_block_library/blocks/cta_button_list_block.html"


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
        clean_html_field(values, "video_code")
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
        template = "gp_wagtail_block_library/blocks/sidebar_link_block.html"


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
        template = "gp_wagtail_block_library/includes/simple_link_w_image.html"


class BaseContactFormChooser(blocks.StructBlock):
    """
    Concrete Blocks should implement a snippet chooser block with
    the concrete version, of the AbstractSimpleContact block, as the "contact_form"
    field.
    """

    class Meta:
        icon = "mail"
        template = "gp_wagtail_block_library/blocks/contact_form_block.html"


# # # # # # # #
#   Blocks    #
# # # # # # # #


class HttpsUrlBlock(blocks.FieldBlock):
    """
    A variation on the base Wagtail URLBlock, which simply wraps a URLField.
    """

    def __init__(self, required=True, help_text=None, max_length=None, min_length=None, **kwargs):
        self.field = HttpsUrlField(
            required=required,
            help_text=help_text,
            max_length=max_length,
            min_length=min_length,
        )
        super().__init__(**kwargs)

    class Meta:
        icon = "site"


class Accordion(blocks.StructBlock):
    """
    An expandable accordion with a heading which, when clicked, expands
    a rich text field beneath it.
    """

    heading = blocks.CharBlock()
    content = blocks.RichTextBlock(required=False)
    embed = blocks.RawHTMLBlock(required=False)

    class Meta:
        icon = "fa-plus-square"
        admin_text = "An accordion with a heading and content that expands when the heading is clicked."
        template = "gp_wagtail_block_library/blocks/accordion_block.html"


class BasicHeroBlock(blocks.StructBlock):
    """
    A basic hero with a required image and optional heading text.
    """

    image = ImageChooserBlock(required=False, help_text="Images will be cropped to 1380x500")
    heading = blocks.CharBlock(
        required=False,
        help_text="Optional heading.",
    )
    use_as_h1 = blocks.BooleanBlock(
        initial=False,
        required=False,
        help_text="Makes the Heading display as an h1 level heading. Note: There should be only one h1 level heading per page.",
    )

    class Meta:
        icon = "fa-file-image-o"
        admin_text = "An banner image with optional heading text"
        template = "gp_wagtail_block_library/blocks/basic_hero_block.html"


class TwoColumn(VideoIframeBlockBase, ReorderableStructBlock):
    """
    Displays a full-width block split in half with an image on one side and text on the other.
    If video is present, the user can click a play button to play the video in a modal.
    """

    image = ImageChooserBlock(
        help_text="If a video is also provided, this image will be used as a thumbnail as well as a fallback on very small screens",
    )

    text_on_left = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="If checked, text will appear on the left side and the image will appear the right",
    )

    heading = blocks.CharBlock(required=False)
    use_as_h1 = blocks.BooleanBlock(
        initial=False,
        required=False,
        help_text="Makes the Heading display as an h1 level heading. Note: There should be only one h1 level heading per page.",
    )
    sub_heading = blocks.RichTextBlock(required=False)
    cta_buttons = blocks.ListBlock(
        CTAButtonBlock(required=False),
        label='"Call to Action" buttons',
        required=False,
    )

    class Meta:
        icon = "fa-columns"
        admin_text = (
            "Two columns, side-by-side on large-enough screens, that display text on one side and an image on the other"
        )
        template = "gp_wagtail_block_library/blocks/two_column_block.html"
        field_order = ["image", "video_code"]


class FullHeroBlock(VideoIframeBlockBase, ReorderableStructBlock):
    image = ImageChooserBlock(required=True)
    heading = blocks.CharBlock(required=True)
    heading_as_h1 = blocks.BooleanBlock(default=True, required=False)
    sub_heading = blocks.RichTextBlock(required=False, features=RICHTEXT_SUBHEADING_FEATURES)

    cta_buttons = CTAButtonList(required=False)

    class Meta:
        icon = "fa-picture-o"
        template = "gp_wagtail_block_library/blocks/full_hero_block.html"
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
        template = "gp_wagtail_block_library/blocks/link_tile_block.html"


class LinkTileNoTitle(LinkTile):
    title = blocks.TextBlock(required=False)


class ManualLinkTileBlock(blocks.StructBlock):
    tiles = blocks.StreamBlock([("tile", LinkTile())], icon="fa-cards")

    class Meta:
        icon = "fa-th"
        template = "gp_wagtail_block_library/blocks/tile_grid_block.html"


class ChildPageLinkTileBlock(blocks.StructBlock):
    heading = blocks.CharBlock(required=False)
    parent_page = blocks.PageChooserBlock()

    class Meta:
        icon = "fa-th"
        template = "gp_wagtail_block_library/blocks/child_page_grid_block.html"


class ExternalContentEmbedBlock(blocks.StructBlock):
    """
    Wagtail admin users can use this block to embed HTTP content using an iframe.
    They must provide a URL that will be the src for the iframe content.

    1. This block uses an iframe to display arbitrary content from another website.
    2. This block requires the definition of an aspect ratio, because it is impossible
       to make any generalizations about the intended size of third-party content.
    """

    url = HttpsUrlBlock(
        help_text="This must be an HTTPs URL.",
        label="URL",
    )
    aspect_ratio = blocks.DecimalBlock(
        help_text=(
            "The height-to-width ratio maintained by the displayed iframe. "
            "If not specified, defaults to letterbox (9/16 = 0.5625). "
            "Minimum value 0.05, maximum value 3.0."
        ),
        min_value=Decimal("0.05"),
        max_value=Decimal("3.0"),
        default=LETTERBOX_RATIO,
        required=False,
    )
    allow_fullscreen = blocks.BooleanBlock(required=False, default=False)

    def clean(self, value):
        """
        Because the default value is not re-supplied to the block
        if no value is added, re-supply it during validation.
        """
        val = super().clean(value)
        aspect_ratios = [
            "aspect_ratio",
        ]
        for ratio in aspect_ratios:
            if ratio not in val or not val[ratio]:
                val[ratio] = LETTERBOX_RATIO
        return val

    class Meta:
        icon = "media"
        template = "gp_wagtail_block_library/blocks/external_content_embed.html"
        label = "Embed External Content"


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
        template = "gp_wagtail_block_library/blocks/columnated_links_block.html"
        label = "Two columns of links"


class HtmlEmbedBlock(blocks.StructBlock):
    """
    Wagtail admin users can use this block to embed content using arbitrary HTML.
    Typically this will be a script tag, in some form. This block is styled to fit
    both the ContentFullWidth page and the ContentSidebar page. This block was
    purpose-built to handle various data-viz and infographic embeds, but should be
    general enough to handle arbitrary embeds.

    This block is easily confused for the ExternalContentEmbedBlock. Below is the key difference.

    1. The "code" here will not be used as a src on an iframe. It will simple be added to
       the DOM where it is meant to be displayed. Therefore the "code" must contain its own
       rendering login. The common format for this is a <div> and <script> tag.

    """

    code = blocks.RawHTMLBlock()
    caption = blocks.CharBlock(
        required=False,
        max_length=40,
        help_text="Caption text will appear below the embed content",
    )

    class Meta:
        icon = "fa-line-chart"
        template = "gp_wagtail_block_library/blocks/html_embed_block.html"
        label = "Embed HTML"

    def clean(self, value):
        fields = super().clean(value)
        clean_html_field(fields, "code")
        return fields


class TwoColumnHtmlEmbedBlock(HtmlEmbedBlock):
    """
    Provides a block consisting of two columns. One column is body content with a heading and a body.
    The other column is the HtmlEmbedBlock

    The order of the block display is up to the content creator.
    """

    copy = CopyBlock()
    text_on_left = blocks.BooleanBlock(
        required=False,
        default=True,
        help_text="If checked, text will appear on the left side and the image will appear the right",
    )

    class Meta:
        icon = "fa-columns"
        template = "gp_wagtail_block_library/blocks/two_column_html_embed_block.html"
        label = "Two Column HTML Embed"


class GPBLNewsletterSignupBlock(blocks.StructBlock):
    """Super projects that override the default form must override get_context to inject
    the concrete form into the block render.
    Example:

        context = super().get_context(value, parent_context=parent_context)
        context['form'] = <PROJECT_CONCRETE_FORM>
        return context
    """

    background_image = ImageChooserBlock(required=True)
    text = blocks.RichTextBlock(features=RICHTEXT_SUBHEADING_FEATURES)

    class Meta:
        icon = "fa-newspaper"
        classnames = "icon fa-light fa-newspaper"
        template = "gp_wagtail_block_library/blocks/newsletter_signup_form.html"

    def get_context(self, value, parent_context=None):
        context = super().get_context(value, parent_context=parent_context)
        context["form"] = GPBLNewsletterSignupForm()
        return context