from __future__ import unicode_literals
from frappe import _
import frappe
import frappe.utils
import frappe.utils.file_manager
from frappe.website.website_generator import WebsiteGenerator
from urllib.parse import urlparse, urlunparse
from frappe.utils import random_string, get_url
from pibicut.pibicut.custom import get_qrcode, file_exists

no_cache = 1


def sanitize_url(url):
    """
    Sanitize the given URL by removing standard ports
    (80, 443) and the "www" subdomain.

    Args:
        url (str): The original URL to be sanitized.

    Returns:
        str: The sanitized URL without standard ports or the "www" subdomain.
    """
    parsed_url = urlparse(url)

    # Check if the port is explicitly included and matches the standard port
    if (parsed_url.scheme == "http" and parsed_url.port == 80) or \
       (parsed_url.scheme == "https" and parsed_url.port == 443):
        # Remove the port from the netloc
        netloc = parsed_url.hostname
    else:
        netloc = parsed_url.netloc

    # Remove the "www" prefix if present
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Reconstruct the URL without the port and "www"
    sanitized_url = urlunparse(parsed_url._replace(netloc=netloc))

    return sanitized_url


class Shortener(WebsiteGenerator):
    RESERVED_PREFIX = "_"
    MAX_RETRIES = 5

    def onload(self):
        self.set_default_file()

    def on_create(self):
        self.set_default_file()

    def set_default_file(self):
        file_name = "/files/logo.png"
        exists = file_exists(file_name)
        if exists:
            self.logo = '/files/logo.png'

    def autoname(self):
        retries = 0

        while retries < self.MAX_RETRIES:
            random_code = f"{self.RESERVED_PREFIX}{random_string(5)}"
            existing_doc = frappe.get_value(
                "Shortener", {"route": random_code}, "name")

            if not existing_doc:
                self.name = random_code
                return

            retries += 1

        # If the loop exits without setting `self.name`, raise an error
        frappe.throw(
            _("Failed to generate a unique code after {0}" +
              " attempts. Please try again.").format(self.MAX_RETRIES))

    @property
    def short_url(self):
        # Get the full URL using get_url
        full_url = get_url(self.name)

        # Sanitize the URL to remove any standard ports and "www"
        sanitized_url = sanitize_url(full_url)

        return sanitized_url

    def validate(self):
        if not (self.long_url.startswith("http")
                or self.long_url.startswith("upi")):
            frappe.throw(_("Please enter a proper URL or UPI"))

    def before_save(self):
        url_short = "".join([self.name])
        qr_code = get_url(url_short)
        logo = self.logo

        self.qr_code = get_qrcode(
            qr_code, logo, url_short, self.name, 'qr_code')
        self.published = True
        self.route = url_short


def increment_redirect_count(name):
    """
    Increments the redirect count for the specified Shortener document.
    Args:
        name (str): The name of the Shortener document to update.
    """
    try:
        # Get the Shortener document by its name
        shortener_doc = frappe.get_doc("Shortener", name)

        # Increment the redirect count
        shortener_doc.redirect_count = (shortener_doc.redirect_count or 0) + 1

        # Save the document back to the database
        shortener_doc.save(ignore_permissions=True)
        frappe.db.commit()

    except frappe.DoesNotExistError:
        frappe.throw(_("Shortener not found: {0}").format(name))

    return shortener_doc.redirect_count


@frappe.whitelist(allow_guest=True)
def increment_redirect(name):
    """
    Wrapper function to whitelist incrementing redirect counts.
    Args:
        name (str): The name of the Shortener document to update.
    """
    print("Name:", name)
    count = increment_redirect_count(name)
    print("Count:", count)
    return {"status": "success", "new_count": count}
