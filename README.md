# GSTT NIR Computing

Welcome to the NIR Computing GitHub! 

![](readme-resources/screenshot.jpg)


It is recommended that you use this GitHub directory with VS Code (which is free) or PyCharm by JetBrains (where you will need an educational license.) The following document highlights how to use and edit this repo in VS Code, and this is easily extendable to PyCharm, with the exception that you do not have to make a Python Intepreter.

## Presentation

⬇️ **Download the slides**

[Download NIR Computing Team GitHub Guide](readme-resources/GitHub_Guide.pdf)

If you are not using either VS Code or PyCharm (not recommended), then please follow the following steps:

```bash
cd Documents
```

Then run:

```bash
ls 
```

To see if there is a folder called GitHub. If there is a folder already, skip to the next step, if there is not, run:

```bash
mkdir GitHub
cd GitHub 
```

Then, run:

```python
git clone https://github.com/GSTT-NIR-Computing/main_database.git
```

Any new projects must be made inside the projects tab. All code needs to be modular, i.e. write as much of it as self-contained functions as possible. When you have written a function, save it as a file in the appropriate folder, under the functions directory.

To start your new project, first create a new folder in the projects tab, then add all of the modules you intend to use into the pyproject.toml file underneath the [project] tab. When you have navigated to your new project folder and want to download the correct packages, run:

```python
python3 -m venv .venv

source .venv/bin/activate

pip3 install ../../"[dev]"
```

As this points back to the .toml file that is in the base directory of this repository.

Ensure that the main script is called main.py, and that it takes its functions from the functions folder, as this is where you will be saving all functions. 

Ensure when you have written your function, you write a corresponding test function within the appropriate place in the functions/tests folder. This will seamlessly integrate your function into GitHub actions.
Importing your newly saved function in your script will usually look like:

```python
from ../functions.filepaths.my_function import my_function
```
