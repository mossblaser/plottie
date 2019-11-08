from setuptools import setup, find_packages

with open("plottie/version.py", "r") as f:
    exec(f.read())

setup(
    name="plottie",
    version=__version__,
    packages=find_packages(),

    # Metadata for PyPi
    url="https://github.com/mossblaser/plottie",
    author="Jonathan Heathcote",
    description="Command-line software for plotting and cutting using Silhouette devices.",
    license="LGPLv3",
    classifiers=[
        "Development Status :: 3 - Alpha",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",

        "Operating System :: POSIX :: Linux",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",

        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
    ],
    keywords="svg plotter cutter silhouette",

    install_requires=["svgoutline", "py_silhouette", "attrs", "toposort", "enum34"],
    
    entry_points={
        "console_scripts": [
            "plottie = plottie.cli:main",
        ],
    }
)
