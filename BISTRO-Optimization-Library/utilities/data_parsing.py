import gzip
import re

import pandas as pd
from lxml import etree


def open_xml(path):
    """
    Open xml and xml.gz files into ElementTree

    Parameters
    ----------
    path: string
        Absolute path of the file to parse
    """
    # Make sure that the path is a string (and not a pathlib.Path object)
    path = str(path)
    if path.endswith('.gz'):
        return etree.parse(gzip.open(path))
    else:
        return etree.parse(path)


def guess_type(s):
    """
    Cast objects to appropriate data types

    Parameters
    ----------
    s: object
        Object whose data type is unknown

    Returns
    -------
    data type

    """
    # test sf_light
    return str
    
    if re.match("^[0-9.]+$", s):
        return float
    elif re.match("^[0-9]+$", s):
        return int
    else:
        return str


def list_attributes(tree):
    """
    Find the unique attribute names of the xml file.

    Parameters
    ----------
    root:

    Returns
    -------
    columns: list
        Columns of the future DataFrame

    """
    root = tree.getroot()

    columns = []
    column_types = []
    for event in root:
        for i in event.items():
            if i[0] not in columns:
                columns.append(i[0])
                column_types.append(guess_type(i[1]))
    return columns, column_types


def create_dataframe(tree, columns, column_types):
    """
    Collect the data and store it in a pandas DataFrame

    Returns
    -------
    : pandas DataFrame
    """
    root = tree.getroot()

    event_data_size = len(columns)
    data = []

    # Reading the data of each event to append values in the correct order.
    for event in root:
        event_data = [None] * event_data_size

        for i in event.items():
            attribute_name = i[0]
            attribute_value = i[1]
            column_index = columns.index(attribute_name)
            event_data[column_index] = column_types[column_index](attribute_value)
        data.append(event_data)

    output_data = pd.DataFrame(data=data, columns=columns)

    return output_data


def extract_dataframe(path):
    tree = open_xml(path)
    columns, column_types = list_attributes(tree)
    output_data = create_dataframe(tree, columns, column_types)
    return output_data
