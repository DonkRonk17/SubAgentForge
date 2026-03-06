from setuptools import setup

setup(
    name="subagentforge",
    version="1.0.0",
    description="Expert Subagent Deployment & Lifecycle Manager",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="ATLAS (Team Brain) for Logan Smith / Metaphy LLC",
    python_requires=">=3.9",
    py_modules=["subagentforge"],
    entry_points={
        "console_scripts": [
            "forge=subagentforge:main",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
    ],
)
