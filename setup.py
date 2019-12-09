from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    LONG_DESCRIPTION = fh.read()

TESTS_REQUIRES = [
    "pylint~=2.3",
    "black",
    "bandit",
]

setup(
    name="standalones2rc",
    description="Automatically join different reservoir simulations into one coupled model",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    url="https://github.com/equinor/standalones2rc",
    author="R&T Equinor",
    packages=find_packages(exclude=["tests"]),
    package_data={"standalones2rc": ["templates/*",]},
    entry_points={"console_scripts": ["standalones2rc=standalones2rc:main"]},
    install_requires=["numpy", "matplotlib", "jinja2"],
    tests_require=TESTS_REQUIRES,
    extras_require={"tests": TESTS_REQUIRES},
    setup_requires=["setuptools_scm~=3.2"],
    use_scm_version=True,
    zip_safe=False,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Natural Language :: English",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
    ],
)
