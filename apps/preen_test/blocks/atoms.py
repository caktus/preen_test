
from django.db.models import TextChoices
from wagtail.core import blocks


class HeadingSizeChoices(TextChoices):
    H1 = "h1"
    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class HeadingColorValues(TextChoices):
    LIGHT = "light"
    DARK = "dark"


class HeadingBaseBlock(blocks.StructBlock):
    """
    Provides basics for Heading text
    """
    size = blocks.ChoiceBlock(choices=HeadingSizeChoices.choices)
    color_value = blocks.ChoiceBlock(choices=HeadingColorValues.choices)


class HeadingBlock(HeadingBaseBlock):
    """
    Basic text heading
    
    Attrs:
        heading: required by default
    """

    heading = blocks.CharBlock()

    class Meta:
        template = "blocks/atoms/heading_block.html"
