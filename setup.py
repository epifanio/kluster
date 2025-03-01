import io
import os
import sys
from shutil import rmtree

from setuptools import find_namespace_packages, setup, Command

# see https://github.com/navdeep-G/setup.py/blob/master/setup.py

# Package meta-data.
NAME = "hstb.kluster"
DESCRIPTION = "Distributed hydrographic multibeam processing system"
URL = "https://github.com/noaa-ocs-hydrography/kluster"
EMAIL = "eric.g.younkin@noaa.gov"
AUTHOR = "Eric Younkin"
REQUIRES_PYTHON = ">=3.8.10"
VERSION = ""

# What packages are required for this module to be executed?
REQUIRED = [
    "bokeh==2.4.2",
    "dask==2021.12.0",
    "distributed==2021.12.0",
    "fasteners==0.16",
    "laspy==2.0.3",
    "matplotlib==3.5.1",  # >=3.3.3 required, FuncAnimation and Pyside2/matplotlib do not play well in 3.2.1
    "numba>=0.53.0",
    "openpyxl==3.0.9",
    "psutil==5.8.0",
    "numpy==1.21.5",  # cannot be 1.19.4, see https://tinyurl.com/y3dm3h86
    "pandas==1.3.5",
    "pyshp==2.1.3",
    "pyepsg==0.4.0",  # cartopy requirement not installed with conda install, duplicates pyproj functionality...
    "pyopengl==3.1.5",
    "pyproj==3.3.0",
    "pyqtgraph==0.12.3",
    "python-geohash==0.8.5",
    "qdarkstyle==3.0.2",
    "s3fs==0.4.2",
    "scipy==1.7.3",
    "shapely==1.8.0",
    "sortedcontainers==2.4.0",
    "watchdog>=2.1.6",
    "xarray==0.20.2",
    "zarr==2.10.3",
    "hstb.drivers @ git+https://github.com/noaa-ocs-hydrography/drivers.git#egg=hstb.drivers",
    "hstb.shared @ git+https://github.com/noaa-ocs-hydrography/shared.git#egg=hstb.shared",
    "vyperdatum @ git+https://github.com/noaa-ocs-hydrography/vyperdatum.git#egg=vyperdatum",
    "bathygrid @ git+https://github.com/noaa-ocs-hydrography/bathygrid.git#egg=bathygrid"
    # note to self about gdal.  I want gdal >= 3.2.3 to get the bag template fix, but qgis appears to only
    #  support gdal=3.2.2 in it's latest version.  So I need to wait on qgis to get the gdal fix.n
    # Pyside stuff
    #  first had to downgrade to PySide2 5.14.1 to avoid shiboken import errors https://bugreports.qt.io/browse/PYSIDE-1257
    #   supposed to be fixed in 5.15.2 but apparently people still see it not working
    #  also hit an import error with matplotlib 3.3.3 with pyside 5.15.2, sticking with 5.13.2 for now
    # 'PySide2==5.13.2',  installed with conda, no distro in pip
    # 'qgis==3.18.0'  Required for GUI, but must be conda installed with PROJ
    # 'vispy==0.6.6'  Required for visualizations
]

# What packages are optional?
EXTRAS = {
    "entwine export": ["entwine", "nodejs"],
}

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you do change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this will only work if 'README.md' is present in your MANIFEST.in file!
try:
    with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
        long_description = "\n" + f.read()
except FileNotFoundError:
    long_description = DESCRIPTION

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    with open(os.path.join(here, "HSTB", "kluster", "__version__.py")) as f:
        exec(f.read(), about)
else:
    about["__version__"] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = "Build and publish the package."
    user_options = []

    @staticmethod
    def status(s):
        """Prints things in bold."""
        print("\033[1m{0}\033[0m".format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.status("Removing previous builds…")
            rmtree(os.path.join(here, "dist"))
        except OSError:
            pass

        self.status("Building Source and Wheel (universal) distribution…")
        os.system("{0} setup.py sdist bdist_wheel --universal".format(sys.executable))

        self.status("Uploading the package to PyPI via Twine…")
        os.system("twine upload dist/*")

        self.status("Pushing git tags…")
        os.system("git tag v{0}".format(about["__version__"]))
        os.system("git push --tags")

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about["__version__"],
    description=DESCRIPTION,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_namespace_packages(
        exclude=["tests", "*.tests", "*.tests.*", "tests.*"]
    ),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],
    # entry_points={
    #     'console_scripts': ['mycli=mymodule:cli'],
    # },
    install_requires=REQUIRED,
    extras_require=EXTRAS,
    include_package_data=True,
    license="CC0-1.0",
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
    ]
    # $ setup.py publish support.
    # cmdclass={
    #     'upload': UploadCommand,
    # },
)
