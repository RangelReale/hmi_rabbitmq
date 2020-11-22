import pathlib
import re

import setuptools

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',  # It excludes inline comment too
    open('hmi_rabbitmq/__init__.py', encoding='utf_8_sig').read()
    ).group(1)

HERE = pathlib.Path(__file__).parent
INSTALL_REQUIRES = (HERE / "requirements.txt").read_text().splitlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="hmi_rabbitmq",
    version=__version__,
    author="Rangel Reale",
    author_email="rangelreale@gmail.com",
    description="Helmion Plugin: RabbitMQ",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/RangelReale/hmi_rabbitmq",
    packages=setuptools.find_packages(),
    package_data={'hmi_rabbitmq': ['py.typed']},
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    test_suite="hmi_rabbitmq.tests",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
