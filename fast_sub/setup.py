from setuptools import setup, Extension

setup(
    name="acb_speedup",
    version="1.0.0",
    description="Speedups for disarm_actual",
    ext_modules=[
        Extension(
            "_acb_speedup", sources=["module.c"], py_limited_api=True
        )
    ],
)
