#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="omnexa_fixed_assets",
    version="1.0.0",
    description="omnexa_fixed_assets application",
    author="ErpGenEx",
    author_email="info@omnexa.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        "frappe>=15.0.0"
    ]
)
