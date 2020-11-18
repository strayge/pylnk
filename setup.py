from setuptools import setup


with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="pylnk3",
    version="0.4.2",
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
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires='>=3.6',
    long_description=long_description,
    long_description_content_type="text/markdown",
)
