# Functions adapted from matplotlib.testing. Credit for the original functions
# goes to the amazing folks over at matplotlib.
from pathlib import Path

import sys
import inspect
import functools

from igraph.drawing import find_cairo

cairo = find_cairo()
if not hasattr(cairo, 'version'):
    cairo = None

__all__ = ("find_image_comparison", "result_image_folder")


result_image_folder = Path('result_images') / 'cairo'


def find_open_image_png_function():
    try:
        from cv2 import imread

        def fun(filename):
            return imread(str(filename))
        return fun
    except ImportError:
        pass

    try:
        import numpy as np
        from PIL import Image

        def fun(filename):
            with Image.open(filename) as f:
                return np.asarray(f)
        return fun
    except ImportError:
        pass

    raise ImportError('PIL+NumPy or OpenCV required to run Cairo tests')


def find_image_comparison():
    def dummy_comparison(*args, **kwargs):
        return lambda *args, **kwargs: None

    if cairo is None:
        return dummy_comparison
    return image_comparison


def are_tests_supported():
    if cairo is None:
        return False, "cairo not found"

    try:
        find_open_image_png_function()
    except ImportError:
        return False, "PIL+NumPy or OpenCV not found"

    return True, ""


def _load_image(filename, fmt):
    if fmt == 'png':
        return find_open_image_png_function()(filename)

    raise NotImplementedError(f'Image format {fmt} not implemented yet')


def _load_baseline_images(filenames, fmt='png'):
    baseline_folder = Path(__file__).parent / 'baseline_images'

    images = []
    for fn in filenames:
        fn_abs = baseline_folder / f'{fn}.{fmt}'
        image = _load_image(fn_abs, fmt)
        assert image is not None
        images.append(image)
    return images


def _load_result_images(filenames, fmt='png'):
    images = []
    for fn in filenames:
        fn_abs = result_image_folder / f'{fn}.{fmt}'
        image = _load_image(fn_abs, fmt)
        assert image is not None
        images.append(image)
    return images


def _compare_image_png(baseline, fig, tol=0):
    import numpy as np

    diff = (np.abs(baseline - fig)).sum()
    if diff <= tol:
        return False
    else:
        return diff


def compare_image(baseline, fig, tol=0, fmt='png'):
    if fmt == 'png':
        return _compare_image_png(baseline, fig, tol=tol)

    raise NotImplementedError(f'Image format {fmt} not implemented yet')


def _unittest_image_comparison(
    baseline_images, tol,
):
    """
    Decorate function with image comparison for unittest.
    This function creates a decorator that wraps a figure-generating function
    with image comparison code.
    """
    def decorator(func):
        old_sig = inspect.signature(func)

        # This saves us to lift name, docstring, etc.
        # NOTE: not super sure why we need this additional layer of wrapping
        # seems to have to do with stripping arguments from the test function
        # probably redundant in this adaptation
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # This decorator is applied to unittest methods
            self = args[0]

            # Three steps:
            # 1. run the function
            func(*args, **kwargs)

            # 2. locate the control and result images
            baselines = _load_baseline_images(baseline_images)
            figs = _load_result_images(baseline_images)

            # 3. compare them one by one
            for i, (baseline, fig) in enumerate(zip(baselines, figs)):
                res = compare_image(baseline, fig, tol)
                self.assertLessEqual(res, tol)

        parameters = list(old_sig.parameters.values())
        new_sig = old_sig.replace(parameters=parameters)
        wrapper.__signature__ = new_sig

        return wrapper

    return decorator


def image_comparison(
    baseline_images,
    tol=0,
):
    """
    Compare images generated by the test with those specified in
    *baseline_images*, which must correspond, else an `ImageComparisonFailure`
    exception will be raised.
    Parameters
    ----------
    baseline_images : list or None
        A list of strings specifying the names of the images generated by
        calls to `.Figure.savefig`.
        If *None*, the test function must use the ``baseline_images`` fixture,
        either as a parameter or with `pytest.mark.usefixtures`. This value is
        only allowed when using pytest.
    tol : float, default: 0
        The RMS threshold above which the test is considered failed.
        Due to expected small differences in floating-point calculations, on
        32-bit systems an additional 0.06 is added to this threshold.
    """
    if sys.maxsize <= 2 ** 32:
        tol += 0.06
    return _unittest_image_comparison(
        baseline_images=baseline_images,
        tol=tol,
    )
