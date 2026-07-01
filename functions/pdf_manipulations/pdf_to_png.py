from pdf2image import convert_from_path
from PIL import Image


def pdf_to_png(pdf_path, output_png_path='output_page.png'):
    """
    Parameters
    ----------
    pdf_path : str
        Path to the source PDF (e.g. 'temp.pdf').
    output_png_path : str, default 'output_page.png'
        Path to write the rendered PNG to.

    Returns
    -------
    bytes
        Raw RGB pixel bytes of the (first/only) rendered page.
    """
    images = convert_from_path(pdf_path)

    for image in images:
        image.save(output_png_path, 'PNG')

    png_in = Image.open(output_png_path)
    png_in = png_in.convert('RGB')

    return png_in.tobytes()
