import setuptools

setuptools.setup(
    name="procsim", # Replace with your own username
    version="0.0.2",
    author="Antonio Sanchez Cabrera",
    author_email="dev.ansaca@gmail.com",
    description="This is a BPMN Diagram process simulator",
    url="https://github.com/ansacaa/prosecco",
    keywords = ['BPMN', 'PROCESS MINING', 'SIMULATOR'],
    packages=setuptools.find_packages(),
    install_requires=[            # I get to this in a second
          'pm4pybpmn',
          'simpy',
          'faker'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
        'Intended Audience :: Developers',      # Define that your audience are developers
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',   # Again, pick a license
        'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    python_requires='>=3.6',
)