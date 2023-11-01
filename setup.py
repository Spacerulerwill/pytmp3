from setuptools import setup, find_packages
import codecs
import os

here = os.path.abspath(os.path.dirname(__file__))

with codecs.open(os.path.join(here, "README.md"), encoding="utf-8") as fh:
    long_description = "\n" + fh.read()

with open("requirements.txt") as f:
    requirements = [line.strip() for line in f.readlines()]

VERSION = '0.0.4'
DESCRIPTION = ' Easily download albums, playlists and songs off YouTube to MP3 format'

# Setting up
setup(
    name="pytmp3",
    version=VERSION,
    author="Spacerulerwill (William Redding)",
    author_email="<williamdredding@gmail.com>",
    description=DESCRIPTION,
    long_description_content_type="text/markdown",
    long_description=long_description,
    packages=find_packages(),
    install_requires=requirements,
    keywords=["python", "youtube", "mp3", "music", "utility", "tool"],
    classifiers=[
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Operating System :: Unix",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
    ]
)