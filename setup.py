"""Setup script for stdf-reader with optional Cython compilation."""
from setuptools import setup

try:
    from Cython.Build import cythonize
    ext_modules = cythonize(
        "pystdf/IO.pyx",
        language_level="3",
    )
except ImportError:
    # Fallback: pure Python without Cython
    ext_modules = []

setup(
    ext_modules=ext_modules,
)
