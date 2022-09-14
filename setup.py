from setuptools import setup, Extension


def main():
    args = dict(
        ext_modules=[
            Extension(
                "_acb_speedup", sources=["fast_sub/module.c"]
            )
        ],
    )

    setup(**args)


if __name__ == "__main__":
    main()
