from setuptools import find_packages, setup


package_name = 'ar01_tools'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    tests_require=['pytest'],
    zip_safe=True,
    maintainer='Artuhinv',
    maintainer_email='vitalik.artuhin@gmail.com',
    description='Diagnostic and command-line tools for the AR-01 rover.',
    license='Proprietary',
    entry_points={
        'console_scripts': [
            'cmd_test = ar01_tools.cmd_test:main',
            'p0_diagnostics = ar01_tools.p0_diagnostics:main',
        ],
    },
)
