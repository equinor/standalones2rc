# standalones2rc

> :warning: This tool is currently in _**alpha**_ version - not production ready.

`standalones2rc` is a tool that automatically creates a reservoir coupled model from standalone models. An arbitrary number of input standalone models can be given.

## Usage

The command

```
standalones2rc ./RC_model_output_folder RNB2020 master.sch summary.inc --datafiles ./some/path1/LOREM.DATA ./some/path2/IPSUM.DATA --slavenames LOR IPS --cpus 4 2 
```
will create a RC model in the folder `./RC_model_output_folder` with simulation case name `RNB2020` from the standalone models `LOREM.DATA` and `IPSUM.DATA`. The slave names to these two input standalone models will be `LOR` and `IPS` in the RC model. In this example, the RC model will be configured such that the two slaves will be using 4 and 2 CPUs, respectively.

The slave names can be almost arbitrary strings (maximum 8 characters), as long as all slave names are unique (in addition, the name `MASTER` is not a valid slave name as this name is used for the automatically generated master `.DATA` file). 
 
The input file `master.sch` is a schedule file given by the user, which will automatically be merged with schedule keywords created by `standalones2rc`. The file `summary.inc` will be included in the summary section of the `MASTER` model.

After running the command, a directory structure similar to the one below will automatically be created:
```
 ./RC_model_output_folder/
                       ├── model/
                       |   ├── RNB2020_MASTER.DATA
                       |   ├── RNB2020_LOR.DATA
                       |   └── RNB2020_IPS.DATA
                       └── include/
                           ├── runspec/
                           |   └── ...
                           ├── grid/
                           |   ├── lor.poro.inc
                           |   └── ips.poro.inc
                           |   └── ...
                           ├── .../
                           |   └── ...
                           └── schedule/
                               └── ...
```
The directory structure is set up such that it agrees with FMU naming conventions. The include files will automatically be copied from the locations used in the different stand alone models, and into the RC model's `include` folder. Also, the include files will be renamed such that it has the slavename as a prefix (i.e. `lor.` or `ips.` in this example), if this prefix doesn't already exist. Also, the include files will automatically be placed in the subfolder associated with the Eclipse section it is used in (regardless of the standalone models follow this convention or not).

## What does standalones2rc do in practice?

It is usually not necessary to know the details below, but for an experienced RC engineer it might be useful to know specifically what <span style="font-family:Courier;">standalones2rc</span> does (and doesn't).

## Linking the slaves to the master

The main idea is that the **slaves model the reservoirs only** (including conversion up to well head conditions), while the **master model takes care of the rest of the production network** (from well head all the way to inlet pressure).

For each well in the slave models, there is automatically created a dummy group with _the same name as the well_ (see illustration below). In all `WELSPECS`, for a given well, the group name (second argument) is changed such that it equals this dummy group. A `GRUPTREE` instance is also added to the slave, linking this newly created dummy group with the group used in the original `WELSPECS` entry from the standalone.

`GRUPMAST` (in the master model) and `GRUPSLAV` (in each slave model) are added, linking all the dummy groups mentioned above between the respective slaves and master.

Since we create quite some extra dummy groups, the third argument in the keyword `WELLDIMS` is increased in all the models such that Eclipse allocates enough memory.

![image](https://user-images.githubusercontent.com/31612826/71574943-44500f00-2aeb-11ea-88f7-82d2514b6dc7.png)

> :book: **Important:**
>   - Well-names must be unique (i.e. the same well name should not be used in different input standalone models).</li>
>   - All groups connected to wells in the standalones (_A_ and _B_ in the example above) must be present in the `GRUPTREE` in the master model.

## Misc. changes done by standalones2rc

* The start date of the master `.DATA` file is set to be the earliest start date among the slaves.
* A `SLAVES` entry is added to the Eclipse master model, defining the slave names and corresponding `.DATA` files.
* All instances of `GRUPNET` and `GCONPROD` in the standalones are commented out when converting them to slaves.
* As it is an simulator requirement, all the dummy groups get automatically a `GCONPROD` or `GCONINJE` entry with default values (i.e. they are transparent to higher level groups guide rates).
* The `PARALLEL` keyword in each slave is changed/removed/added according to the user specified number of CPUs (using the `--cpu` argument to `standalones2rc`).

## Installation

### Create a virtual environment (if you don't already have one)

You need `Python3` to run this tool. Internally in Equinor, you can get it to run e.g. by:
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
