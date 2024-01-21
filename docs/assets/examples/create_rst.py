"""
name: "create_rst.py"
title: "Python Script to Create RST Files for Sphinx"
authors: "felix@42sol.eu"
license: "http://www.apache.org/licenses/LICENSE-2.0"
created: "2023-01-21"
modified: "2024-01-21"

description: |
    Python script to generate documentation in RST format.
    Used for the `build123d` documentation of examples.    
    TODO: check if we could add Sphinx-Gallery to the project https://sphinx-gallery.github.io/stable/advanced.html
    NOTE: https://yaml-multiline.info/ is a good site to learn about multiline yaml strings.
has_builder_mode: false
has_algebra_mode: false
image_files:
    - "none.png"
"""
# ---------------------------------------------------------------------------------------------
# [Imports]
import sys
import ast # see https://docs.python.org/3/library/ast.html
from os import getcwd as pwd    # see https://docs.python.org/3/library/os.html#os.getcwd
import dataclasses as dc        # see https://docs.python.org/3/library/dataclasses.html
from dataclasses import dataclass, asdict
from typing import List, Dict   # see https://docs.python.org/3/library/typing.html
from pyperclip import copy      # see https://pyperclip.readthedocs.io/en/latest/
from ruamel.yaml import YAML    # see https://yaml.readthedocs.io/en/latest/index.html
#                                 and for yaml tutorial see https://www.cloudbees.com/blog/yaml-tutorial-everything-you-need-get-started
from shellrunner import X       # see https://github.com/adamhl8/shellrunner
# ---------------------------------------------------------------------------------------------
# [Definitions]
log = print
stdout = print
stderr = print
Yes = True
No = False
def debug(message):
    pass

# ---------------------------------------------------------------------------------------------
# [Parameters]
# - none 

# ---------------------------------------------------------------------------------------------
# [Classes]

@dataclass
class Example:
    name: str
    title: str
    authors: str
    license: str
    created: str
    modified: str
    description: str
    has_builder_mode: bool
    has_algebra_mode: bool
    image_files: List[str]

# ---------------------------------------------------------------------------------------------
# [Functions]

def wait_for_user():
    input("Press Enter to continue...")
    
def remove_extension( file_name ):
    output = file_name 
    if output.find('.') != -1:
        output = file_name.split('.')[:-1][0]
    return output

def do_index_rst(file_name, title, has_builder_mode=Yes, has_algebra_mode=No):
    file_name = remove_extension( file_name )
    
    modes = ""
    if has_builder_mode:
        modes += '|Builder| '
    if has_algebra_mode:
        modes += '|Algebra| '

    index_rst = """
    .. grid-item-card:: {title} {modes}
            :img-top: assets/examples/thumbnail_{file_name}_01.{extension}
            :link: examples-{file_name}
            :link-type: ref
    """
    output = index_rst.format( title=title, modes=modes, file_name=file_name, extension='png' )
    return output

def do_code_rst(code_file, has_builder_mode=Yes, has_algebra_mode=No, start_after = "[Code]", end_before = "[End]"):
    builder_mode = "Builder"
    builder_algebra = "Algebra"    
    code_file = remove_extension( code_file )
    
    code_template = """
.. dropdown:: |{mode}| Reference Implementation ({mode} Mode) 

    .. literalinclude:: ../examples/{file}.py
        :start-after: {start_after}
        :end-before: {end_before}
    """
    output = ""
    if has_builder_mode:
        output += code_template.format( mode=builder_mode, file=code_file, start_after=start_after, end_before=end_before )
    if has_algebra_mode:
        if code_file.find("algebra") == -1:
            code_file = code_file + "_algebra"
        output += code_template.format( mode=builder_algebra, file=code_file, start_after=start_after, end_before=end_before )

    return output

def do_images_rst(list_of_files):
    output = "\n.. dropdown:: More Images\n\n"

    for file in list_of_files:
        output += f"""    .. image:: assets/examples/{file}
        :align: center\n\n""" 

    return output

def do_details_rst(file_name, title, description, image_files=['example_build123d_customizable_logo_01.png'], has_builder_mode=Yes, has_algebra_mode=No, start_after = "[Code]", end_before = "[End]"): 
    file_name = remove_extension( file_name )
    code_file = file_name
    output_core = """
.. _examples-{example_name}:

{title}
--------------------------------
.. image:: assets/examples/{image_file_01}
    :align: center

\n\n{description}\n\n"""

    output = output_core.format( example_name=file_name, title=title, description=description, image_file_01=image_files[0] )
    if len(image_files) > 1:
        output += do_images_rst(image_files[1:])
    output += do_code_rst(code_file, has_builder_mode=has_builder_mode, has_algebra_mode=has_algebra_mode, start_after=start_after, end_before=end_before)

    return output


def dict_to_dataclass(the_class, data):
    debug(f"{the_class=}, {data=}")
        
    try:
        #field_types = {field.name: field.type for field in dc.fields(the_class)}
        #return the_class(**{item: dict_to_dataclass(field_types[item], data[item]) for item in data})
        return the_class(**data)
    
    except:
        stderr(f"Error: Could not convert dictionary to dataclass.")
        return data  
    
def get_data_from_docstring_in_file(file_path):
    """
    Extracts the docstring from a Python file.

    Parameters:
    - file_path (str): Path to the Python file.

    Returns:
    - data: dict or Example
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        tree = ast.parse(file.read(), filename=file_path)

    # Find the first string literal, which is the docstring
    docstring_node = next((node for node in ast.walk(tree) if isinstance(node, ast.Str)), None)

    if docstring_node:
        data = yaml.load(docstring_node.s)
        data = dict_to_dataclass(Example, data)
        return data
    else:
        return None
    

    
def get_data_from_yaml_file(file_path="examples.yaml"):
    """
    Opens a yaml file and returns the content as a dictionary.

    Parameters:
    - file_path (str): Path to the yaml file.

    Returns:
    - dict: The content of the yaml file.
    """
    log(pwd())
    with open(file_path, 'r', encoding='utf-8') as file:
        data = yaml.load(file.read())
    data = dict_to_dataclass(Example, data)
    return data


# ---------------------------------------------------------------------------------------------
# [Code]
if __name__ == "__main__":
    yaml = YAML(typ='safe')

    # Example usage
    file_path = "../../../examples/benchy_v2024.py"
    example = get_data_from_docstring_in_file(file_path)
    
    stdout(f"Data from docstring in file '{file_path}':")
    if type(example) == Example:
        stdout(f"Example: {example.name}")
    else:
        stderr(f"Error: Could not convert dictionary to dataclass.")
    
    index_rst = do_index_rst(example.name, title=example.title, has_builder_mode=example.has_builder_mode, has_algebra_mode=example.has_algebra_mode) 
    details_rst = do_details_rst(example.name, title=example.title, description=example.description, image_files=example.image_files,  has_builder_mode=example.has_builder_mode, has_algebra_mode=example.has_algebra_mode) 
    copy(index_rst)
    stdout('index copied to clipboard... please add it to the `examples_1.rst` above `NOTE 01`')
    wait_for_user()
    copy(details_rst)
    stdout('details copied to clipboard...  please add it to the `examples_1.rst` above `NOTE 02`')
    wait_for_user()
    stdout('now running sphinx via `make html`')
    X([
        'cd ../../',
        'make html',
        'cd assets/examples',
    ])

# [End]