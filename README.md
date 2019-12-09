# standalones2rc

Tool that automatically creates a reservoir coupled model from standalone models.

## Usage

You need Python3 to run this tool. Internally in Equinor, you can get it to run e.g. by:

### Create a virtual environment (if you don't already have one)

```cshell
setenv MY_NEW_VENV ./some_path_where_i_want_my_new_venv

setenv PYTHON_VERSION "3.6.4"
source /prog/sdpsoft/env.csh
python3 -m virtualenv --no-site-packages $MY_NEW_VENV
source $MY_NEW_VENV/bin/activate.csh
```

### Install or upgrade `standalones2rc`

Make sure you virtual environment is active (run e.g. `which python` to see which Python
binary is on your path). Then
```
pip install --upgrade git+https://github.com/equinor/standalones2rc
```
