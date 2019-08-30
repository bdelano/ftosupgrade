# Collection of scripts to upgrade FTOS
This is specific to our company build so it most likely will not work out of the box with your environment.  The code was put together quickly and isn't meant to be pretty or user friendly

<!-- MDTOC maxdepth:6 firsth1:2 numbering:0 flatten:0 bullets:1 updateOnSave:1 -->

- [Intallation](#intallation)   
- [Distributing your binary files](#distributing-your-binary-files)   
   - [notes](#notes)   
- [Running the upgrade script](#running-the-upgrade-script)   
   - [Prepare the Switches for Upgrade](#prepare-the-switches-for-upgrade)   
   - [Upgrade the Switch](#upgrade-the-switch)   
   - [Backout /  Downgrade](#backout-downgrade)   
- [To Do](#to-do)   

<!-- /MDTOC -->
## Intallation
Its probably easiest to just install this in a virtual environment so as not to mess with the current modules
* use a *nix* box, tested on ubuntu 16.4
* create environment `virtualenv ftosupgrade`
* then run `source ftosupgrade/bin/activate`
* add the required python modules
  * MySQL-python (only if you are going to use a remote sql server)
  * paramiko
  * scp
  * pexpect
  * termcolor
  * terminaltables
* clone this repository
* add a `localauth.py` file with the necessary information (see example file)
* add the path to the repository to your users path or setup a link

## Distributing your binary files
* update `uploadbin.py` to accomodate your list of hostnames
  * currently this uses a mysql connection to pull this information but you should be able to pass any list of hostnames the `makeforks` function
* run `updatebin.py` to push your code version up

### notes
* assumes your binary files are in a directory called '/tftpboot/Dell/', you can change this in `uploadbin.py`

## Running the upgrade script

### Prepare the Switches for Upgrade
* opengear connectivity will be validated and will be listed in the prepare output
* prompt will be compared between opengear and ssh to device
* build directories to support pre,post and log files
* check that binfile exists on the remote devices and is valid (md5)
* add your binary to the 'alternate' slot A or B
  * alternate is determined by whichever boot slot is currently in use
* change the boot order in the config to load the alternate slot
* run pre upgrade commands (for diffs)
  * `show alarm |no-more`(fail if any exist)
  * `show vlt br |no-more` (fail if unexpected results)
  * `show hardware stack-unit 1 unit 0 execute-shell-cmd “ps” |no-more` (fail if status is blocking and port is up)
  * `show int desc |no-more`
  * `show run |no-more`
  * `show logging |no-more`
  * `show lldp nei |no-more`
* all command output will be copied to a file in the `~/ftosupgrade/<devicename>/<PRE>` directory
* all raw output will sent to `<devicename>/raw.log`
* a JSON file `<devicename>/devinfo.json` will be created to track history of the upgrade used for any necessary stateful information

### Upgrade the Switch
* check if the switch is already upgraded
* login to switch via opengear connection
* run the `reload` command acknowledge and wait for prompt
* login to switch again via ssh
* run post checks (see pre-check commands)
* run diffs between pre and post checks
* look for any errors/anomolies (this needs to be defined)
* esclate if any issues

### Backout /  Downgrade
* restore previous boot config
* reload device?

## To Do
* reload a switch with the upgrade script to get the right expects sorted
* setup post checks
* figure out how to diff the pre/post files so it makes sense to the user
* test full upgrade
* re-rwrite the binary upload script to use pexpect so no dependence on paramiko
