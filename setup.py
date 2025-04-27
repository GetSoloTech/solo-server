from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="solo-server",
    version="0.4.2",
    author="Dhruv Diddi",
    author_email="dhruv.diddi@gmail.com",
    description="Platform for Hardware Aware Inference.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GetSoloTech/solo-server",
    packages=find_packages(include=["solo_server", "solo_server.*"]),
    include_package_data=True,
    package_data={
        "solo_server.config": ["*.yaml"],
    },
    install_requires=[
        "typer",
        "GPUtil",
        "psutil",
        "requests", 
        "rich",
        "huggingface_hub",
        "pydantic",
    ],
    extras_require={
        "dev": ["pytest", "black", "isort"],
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "solo=solo_server.cli:app",
        ],
    },
)