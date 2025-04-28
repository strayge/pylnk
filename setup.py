from setuptools import setup


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="pylnk3",
    version="0.4.3",
    py_modules=["pylnk3"],
    entry_points={
        'console_scripts': [
            'pylnk3 = pylnk3:cli',
        ],
    },
    description="Windows LNK File Parser and Creator",
    author="strayge",
    author_email="strayge@gmail.com",
    url="https://github.com/strayge/pylnk",
    keywords=["lnk", "shortcut", "windows"],
    license="GNU Library or Lesser General Public License (LGPL)",
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.9',
    long_description=long_description,
    long_description_content_type="text/markdown",
)
