import sys
from setuptools import setup, Extension


def main():
    args = dict(
        name="acb-py",
        version="1.0.4",
        description="Library for reading/extracting ACB files.",
        packages=["acb"],
        ext_modules=[
            Extension(
                "_acb_speedup", sources=["fast_sub/module.c"], py_limited_api=True
            )
        ],
        entry_points = {
            "console_scripts": ["acbextract=acb.__main__:main"],
        },
    )

    setup(**args)


if __name__ == "__main__":
    main()
