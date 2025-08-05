from setuptools import setup
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pycrucible",
    version="1.0.0",
    author="mkywall",
    author_email="mkywall3@gmail.com",
    description="Python Client for the Crucible API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="BSD",
    url = "",
    
    package_dir = {'pycrucible':'.'},
    packages=['pycrucible'],

    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
        "pytz>=2021.1",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.812",
        ],
    },
)
