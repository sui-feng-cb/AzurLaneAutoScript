import os

import cv2
import numpy as np

from module.base.utils import crop, image_size


class ImageError(Exception):
    """ Error when parsing images """
    pass


class ImageInvalidResolution(ImageError):
    """ Image is not in 1280x720 """
    pass


def load_folder(folder, ext='.png'):
    """
    Args:
        folder (str): Template folder contains images.
            Image shape: width=96, height=96, channel=3, format=png.
            Image name: Camel-Case, such as 'PlateGeneralT3'. Suffix in name will be ignore.
            For example, 'Javelin' and 'Javelin_2' are different templates, but have same output name 'Javelin'.
        ext (str|list[str]): File extension.

    Returns:
        dict: Key: str, image file base name. Value: full filepath.
    """
    if not os.path.exists(folder):
        return {}

    out = {}
    for file in os.listdir(folder):
        name, extension = os.path.splitext(file)
        if (isinstance(ext, str) and extension == ext) \
                or (isinstance(ext, list) and extension in ext):
            out[name] = os.path.join(folder, file)

    return out


def pack(img_list):
    """
    Stack images vertically.

    Args:
        img_list (list): List of image

    Returns:
        np.ndarray:
    """
    image = cv2.vconcat(img_list)
    return image


def unpack(image):
    """
    Split images vertically.

    Args:
        image:

    Returns:
        list: List of np.ndarray.
    """
    size = image_size(image)
    if size == (1280, 720) or size[0] == round(size[1] * 16 / 9) \
            or size[0] != 1280 or size[1] % 720 != 0:
        return [image]
    else:
        return [crop(image, (0, n * 720, 1280, (n + 1) * 720)) for n in range(size[1] // 720)]


def resize_image(image):
    """
    Crop and resize to 1280x720.

    Args:
        image:

    Returns:
        np.ndarray:
    """
    size = image_size(image)
    width, height = size
    if size == (1280, 720):
        return image
    elif width == round(height * 16 / 9):
        return cv2.resize(image, (1280, 720), interpolation=cv2.INTER_LANCZOS4)
    elif width != 1280 or height % 720 != 0:
        if width / height < 16 / 9:
            crop_height = width * 9 / 16
            y1 = round(height / 2 - crop_height / 2)
            y2 = round(height / 2 + crop_height / 2)
            crop_img = crop(image, (0, y1, width, y2))
        else:
            crop_width = height * 16 / 9
            x1 = round(width / 2 - crop_width / 2)
            x2 = round(width / 2 + crop_width / 2)
            crop_img = crop(image, (x1, 0, x2, height))
        return cv2.resize(crop_img, (1280, 720), interpolation=cv2.INTER_LANCZOS4)
    else:
        raise ImageInvalidResolution(f'Unexpected image size: {size}')


def get_similarity(image):
    """
    Get similarity from a image.

    Args:
        image:

    Returns:
        float: 0-1. Similarity.
    """
    size = image_size(image)
    if size == (1280, 720):
        return 0.85
    elif size[0] == round(size[1] * 16 / 9) or size[0] != 1280 or size[1] % 720 != 0:
        return 0.69
    else:
        return 0.85
