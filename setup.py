from setuptools import setup

# Reading long description from README
with open("README.md", "r", encoding='UTF-8') as fh:
    long_description = fh.read()

# Reading requirements from requirements.txt
with open("requirements.txt", "r", encoding='UTF-8') as fh:
    requirements = fh.read().splitlines()
with open("./tests/requirements-test.txt", "r", encoding='UTF-8') as fh:
    test_requirements = fh.read().splitlines()

setup(
    name="smtpymailer",
    version="0.0.6",
    author="Lewis Morris",
    author_email="lewis@arched.dev",
    description="A emailing python library for emailing from alternative domains - DNS entries etc need to be assigned (not used for spamming).",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/lewis-morris/smtpymailer",
    packages=["smtpymailer"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        'dev': test_requirements
    },
    include_package_data=True,
)
