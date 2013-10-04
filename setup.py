from setuptools import setup

setup(
    name='patterns',
    version='0.1.2',
    author='Alexander Schepanovski',
    author_email='suor.web@gmail.com',

    description='Pattern matching for python',
    long_description=open('README.rst').read(),
    url='http://github.com/Suor/patterns',
    license='BSD',

    packages=['patterns'],
    install_requires=['meta'],

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',

        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Pre-processors',
        'Intended Audience :: Developers',
    ]
)
