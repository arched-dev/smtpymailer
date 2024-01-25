from setuptools import setup

with open("README.md", "r", encoding='UTF-8') as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding='UTF-8') as fh:
    requirements = fh.read().split("\n")

setup(
    name="smtpy-mailer",
    version="0.0.1",
    author="Lewis Morris",
    author_email="lewis@arched.dev",
    description="A emailing python library for emailing from alternative domains - dns entries etc need to be assigned (not used for smapping).",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lewis-morris/smtpy-mailer",
    packages=["googlesearch"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    install_requires=[requirements],
    include_package_data=True,
)
