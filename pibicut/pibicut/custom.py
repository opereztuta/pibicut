# -*- coding: utf-8 -*-
# Copyright (c) 2021, PibiCo and contributors
# For license information, please see license.txt
from frappe.utils.file_manager import get_file_path, save_file, remove_file
from frappe import log_error
import os
import qrcode
from PIL import Image
import base64
from io import BytesIO


def get_qrcode(input_data, logo=None, file_name=None, dn=None, df=None):
    """
    Generates a QR code with an optional logo embedded in the center.

    Args:
        input_data (str): The data to encode into the QR code.
        logo (str, optional): The file path to the logo image.
        Defaults to None.
        file_name (str, optional): The desired file name for the QR code image.
        dn (str, optional): The name of the document.
        df (str, optional): The field name to attach to.

    Returns:
        str: The URL of the saved file or base64-encoded
          image if no filename is provided.
    """

    # Create the QR code object
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=24,
        border=4,
    )
    qr.add_data(input_data)
    qr.make(fit=True)

    # Create the QR code image
    qr_img = qr.make_image(fill_color="black",
                           back_color="white").convert('RGB')

    # If a logo path is provided, add the logo to the QR code

    if file_exists(logo):
        logo_img = Image.open(get_file_path(logo))

        # Resize the logo to fit within the QR code
        logo_width, logo_height = logo_img.size
        qr_width, qr_height = qr_img.size
        logo_max_size = min(qr_width, qr_height) // 4
        if logo_width > logo_max_size or logo_height > logo_max_size:
            logo_img = logo_img.resize((logo_max_size,
                                        logo_max_size), Image.LANCZOS)

        # Calculate position to center the logo
        logo_x = (qr_width - logo_img.size[0]) // 2
        logo_y = (qr_height - logo_img.size[1]) // 2

        # Place the logo in the center of the QR code
        qr_img.paste(logo_img, (logo_x, logo_y), logo_img)

    # Save the QR code to a temporary buffer and encode it as base64
    temp = BytesIO()
    qr_img.save(temp, format='PNG')
    temp.seek(0)
    # If no file name or document details are provided, return the
    # base64-encoded image
    if not file_name or not dn or not df:
        b64 = base64.b64encode(temp.read())
        return "data:image/png;base64,{0}".format(b64.decode("utf-8"))

    # Provide a proper file name for saving the image
    file_name = f"{file_name}.png"

    if file_exists(file_name):
        remove_file(file_name)

    # Save the file to the Frappe file system using raw binary data
    file_doc = save_file(
        fname=file_name,
        content=temp.getvalue(),  # Use raw image bytes
        dt="Shortener",
        dn=dn,
        df=df,
        folder=None,
        is_private=0  # Set to 1 if you want the file to be private
    )

    # Return the file URL for attachment
    return file_doc.file_url


def file_exists(file_name):
    """
    Check if a file exists in the public or private files directory.

    Args:
        file_name (str): The name of the file to check.

    Returns:
        bool: True if the file exists, False otherwise.
    """
    try:
        file_path = get_file_path(file_name)
        return os.path.exists(file_path)
    except Exception as e:
        log_error(f"Error checking file existence: {e}", "File Manager")
        return False
