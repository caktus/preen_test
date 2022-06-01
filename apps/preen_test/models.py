from django.db import models


# Create your models here.

class ContentFullWidth(PreviewablePage):
    """
    A page with full-width content, no side bar.
    """

    body = fields.StreamField(
        _full_width_blocks(),
        blank=True,
    )

    content_panels = PreviewablePage.content_panels + [StreamFieldPanel("body")]

    search_fields = Page.search_fields + [
        index.SearchField("body"),
    ]

    template = "pages/content_full_width_page.html"


class ContentSidebarPage(PreviewablePage):
    """
    A page with a content well and a right-aligned sidebar
    """

    header = fields.StreamField(
        [
            ("banner", gg_blocks.GGBasicHeroBlock()),
        ],
        blank=True,
    )

    body = fields.StreamField(
        _side_bar_body_blocks(),
        blank=True,
    )

    side_bar = fields.StreamField(
        _side_bar_blocks(),
        blank=True,
    )

    secondary_content = fields.StreamField(
        _full_width_blocks(),
        blank=True,
    )

    content_panels = PreviewablePage.content_panels + [
        StreamFieldPanel("header"),
        StreamFieldPanel("body"),
        StreamFieldPanel("side_bar"),
        StreamFieldPanel("secondary_content"),
    ]

    search_fields = Page.search_fields + [
        index.SearchField("header"),
        index.SearchField("body"),
        index.SearchField("side_bar"),
        index.SearchField("secondary_content"),
    ]

    template = "pages/content_sidebar_page.html"
