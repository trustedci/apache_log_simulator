import random

class Page:
    def __init__(self, proto, domain, path, status=200, size=None, links=[]):
        self.proto = proto
        self.domain = domain
        self.path = path
        self.status = status

        self.links = links
        self.size = size
        self.external_links = []
        self.images = []
        self.external_images = []
        self.css = []
        self.external_css = []
        self.scripts = []
        self.external_scripts = []
        self.email_addrs = []

    def _add_info(self, destination, value):
        if value not in destination:
            destination.append(value)

    def random_link(self):
        if not self.links:
            return None
        index = random.randint(1, len(self.links))
        return self.links[index - 1]

    def full_uri(self):
        return '%s://%s%s' % (self.proto, self.domain, self.path)

    def full_address(self):
        return '%s%s' % (self.domain, self.path)

    def add_link(self, link):
        self._add_info(self.links, link)

    def add_external_link(self, link):
        self._add_info(self.external_links, link)

    def add_image(self, image_path):
        self._add_info(self.images, image_path)

    def add_external_image(self, image_path):
        self._add_info(self.external_images, image_path)

    def add_script(self, script_path):
        self._add_info(self.scripts, script_path)

    def add_external_script(self, script_path):
        self._add_info(self.external_scripts, script_path)

    def add_css(self, css_path):
        self._add_info(self.css, css_path)

    def add_external_css(self, css_path):
        self._add_info(self.external_css, css_path)

    def add_email(self, email_address):
        self._add_info(self.email_addrs, email_address)