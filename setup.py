from setuptools import setup


setup(
    name='django-timeslot-lottery',
    version='0.1',
    description='Let people bid for timeslots and pick worthy winners',
    license='GPL',
    install_requires=[
        'Django>=1.7',
        'django-model-utils>=2.1.0',
        'django-jsonfield',
    ],
)
