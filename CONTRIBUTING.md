# Contributing to Where is Ben Nevis?

## Developer installation

Clone the repository and install with full extras using:
```
pip install -e .[dev,extras]
```

## Explore the data set

Use `gb.py` to plot the full data set in `results/gb.png`.

Zoom in on e.g. the NY square using `gb.py NY`, or zoom even further with e.g. `gb.py NY3`

## Check the quality of the interpolants

Use `interpolation.py` to create a whole bunch of plots showing cross-sections of the landscape, all stored in `results`.

## Documentation

Every method and every class should have a [docstring](https://www.python.org/dev/peps/pep-0257/) that describes in plain terms what it does, and what the expected input and output is.
Each docstring should start with a [single sentence](https://www.python.org/dev/peps/pep-0257/#one-line-docstrings) explaining what it does.
Optionally, this can be followed by a blank line and a more elaborate explanation.

Docstrings can  make use of [reStructuredText](http://docutils.sourceforge.net/docs/user/rst/quickref.html).
For example, you can link to other classes and methods by writing ```:class:`nevis.Coords` ``` and  ```:meth:`gb()` ```.

Sphinx [Sphinx](http://www.sphinx-doc.org/en/stable/) is used to convert the docstrings into a HTML format, hosted on [http://nevis.readthedocs.io](http://nevis.readthedocs.io).
The order in which the classes and methods appear here is specified by the `.rst` file in the `docs` directory.

## Testing

At the moment, no unit tests are implemented.
(Continuous integration testing [would require the data to be kept on github](https://github.com/CardiacModelling/BenNevis/issues/56), which I haven't explored.)

### Unit testing

When implemented, will use the `unittest` module.
Tests are stored in the `nevis.tests` module.
To run, use

```
python -m unittest
```

### Style testing

Use `flake8`, or `flake8 -j4` to use up to 4 cores.
Flake8 should be installed automatically if you added the `dev` switch when installing (see above).
Some style guidelines are ignored, as specified in the file `.flake8`.

### Documentation testing

Documentation can be built locally with

```
cd docs
make clean
make html
```

To test if all classes and methods are covered, use

```
python nevis/tests/docs.py
```

### Github actions

Workflows for github actions are stored in `.github/workflows`.

## Uploading to PyPI

If you're me, you can upload to PyPI using:

```
python setup.py sdist bdist_wheel
twine upload dist/*
rm build/ dist/ -rf
```

Remember you can only do this **once per version number**.
