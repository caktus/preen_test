from django.test import RequestFactory, TestCase

from bs4 import BeautifulSoup
from wagtail.core.models import Page, Site
from wagtail.tests.utils import WagtailTestUtils


class BasePageTest(TestCase, WagtailTestUtils):
    def get_request(self):
        self.request = self.factory.get("/")
        self.response = self.home.serve(self.request)
        self.response.render()
        self.soup = BeautifulSoup(self.response.content, "html5lib")

    def get_search(self, query):
        self.response = self.client.get("/search/", {"query": query})
        self.soup = BeautifulSoup(self.response.content, "html5lib")

    def setUp(self):
        self.factory = RequestFactory()
        self.site = Site.objects.get()
        self.root = Page.get_first_root_node()

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
