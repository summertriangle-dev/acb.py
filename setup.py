import sys
from setuptools import setup, Extension


def main():
    args = dict(
        ext_modules=[
            Extension(
                "_acb_speedup", sources=["fast_sub/module.c"], py_limited_api=True
            )
        ],
    )

    setup(**args)


if __name__ == "__main__":
    main()
