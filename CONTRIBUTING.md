# Contributing to Where's Ben Nevis?

## Developer installation

Clone the repository and install with full extras using:
```
pip install -e .[dev,extras]
```

## Explore the data set

Use `gb.py` to plot the full data set in `results/gb.png`.

Zoom in on e.g. the NY square using `gb.py NY`, or zoom even further with `gb.py NY3`

## Check the quality of the interpolants

Use `interpolation.py` to create a whole bunch of plots showing cross-sections of the landscape, all stored in `results`.

## Testing

At the moment, no unit tests are implemented.
(Continuous integration testing would require the data to be kept on github, which I haven't explored.)

### Style testing

Use `flake8`, or `flake8 -j8` to use up to 8 cores.
This should be installed automatically if you added the `dev` switch when installing (see above).
Some errors are ignored, as specified in the file `.flake8`.

### Github actions

Workflows for github actions are stored in `.github/workflows`.
At the moment, this only does style testing.

## Uploading to PyPI

If you're me, you can upload to PyPI using:

```
python setup.py sdist bdist_wheel
twine upload dist/*
rm build/ dist/ -rf
```

Remember you can only do this **once per version number**.
