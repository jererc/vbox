from setuptools import setup, find_packages

setup(
    name='vbox',
    version='2026.01.17.070218',
    author='jererc',
    author_email='jererc@gmail.com',
    url='https://github.com/jererc/vbox',
    packages=find_packages(exclude=['tests*']),
    python_requires='>=3.10',
    install_requires=[
    ],
    extras_require={
        'dev': ['flake8', 'pytest'],
    },
    include_package_data=True,
)
