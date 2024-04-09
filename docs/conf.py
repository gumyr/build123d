# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import build123d

build123d_path = os.path.dirname(os.path.abspath(os.getcwd()))
source_files_path = os.path.join(build123d_path, "src", "build123d")
sys.path.insert(0, source_files_path)
sys.path.append(os.path.abspath("sphinxext"))
sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("../"))

# -- Project information -----------------------------------------------------

project = "build123d"
copyright = "2022, Gumyr"
author = "Gumyr"

# The full version, including alpha/beta/rc tags
# version = build123d.__version__
release = build123d.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    #    "sphinx_autodoc_typehints",
    "sphinx.ext.autodoc.typehints",
    "sphinx.ext.doctest",
    "sphinx.ext.graphviz",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.viewcode",
    "sphinx_design",
    "sphinx_copybutton",
    "hoverxref.extension",
]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_use_keyword = True
napoleon_custom_sections = None

autodoc_typehints = ["signature"]
# autodoc_typehints = ["description"]
# autodoc_typehints = ["both"]

autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "member-order": "alphabetical",
    "show-inheriance": False,
}

# autodoc_mock_imports = ["OCP"]

# Sphinx settings
add_module_names = False
python_use_unqualified_type_names = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# html_theme = "alabaster"
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# -- Options for hoverxref -------------------------------------------------
hoverxref_role_types = {
    "hoverxref": "tooltip",
    "ref": "tooltip",  # for hoverxref_auto_ref config
    "confval": "tooltip",  # for custom object
    "mod": "tooltip",  # for Python Sphinx Domain
    "class": "tooltip",  # for Python Sphinx Domain
    "meth": "tooltip",  # for Python Sphinx Domain
    "func": "tooltip",  # for Python Sphinx Domain
}

hoverxref_roles = [
    "class",
    "meth",
]

hoverxref_domains = [
    "py",
]

html_logo = "assets/build123d_logo/logo.svg"
