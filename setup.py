# ! important
# see https://stackoverflow.com/a/27868004/1497139
from setuptools import setup
from collections import OrderedDict

# read the contents of your README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyOnlineSpreadSheetEditing',
    version='0.0.1',

    packages=['spreadsheet',],
    author='Wolfgang Fahl',
    author_email='wf@bitplan.com',
    maintainer='Wolfgang Fahl',
    url='https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing',
    project_urls=OrderedDict(
        (
            ("Documentation", "http://wiki.bitplan.com/index.php/pyOnlineSpreadSheetEditing"),
            ("Code", "https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing"),
            ("Issue tracker", "https://github.com/WolfgangFahl/pyOnlineSpreadSheetEditing/issues"),
        )
    ),
    license='Apache License',
    description='python Online SpreadSheet Editing tool with configurable enhancer/importer and check phase',
    install_requires=[
          'pyLodStorage~=0.0.81',
          'pyFlaskBootstrap4~=0.2.19',
          'pandas~=1.3.4'
    ],
    classifiers=[
            'Programming Language :: Python',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
            'Programming Language :: Python :: 3.9'
    ],
    long_description=long_description,
    long_description_content_type='text/markdown'
)
